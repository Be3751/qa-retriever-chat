import os
import json
import logging
from typing import Any, AsyncGenerator, Optional, Union

from openai import AzureOpenAI
from approaches.approach import Approach
from core.messagebuilder import MessageBuilder
from core.modelhelper import get_token_limit
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
import dotenv

dotenv.load_dotenv()
aoai_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT_URL"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
)

class ChatReadRetrieveReadApproach(Approach):
    # Chat roles
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

    NO_RESPONSE = "0"

    # TODO: 適切なプロンプトに変更する
    """
    Simple retrieve-then-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
    top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion
    (answer) with that prompt.
    """
    system_message_chat_conversation = """Assistant helps the company employees with their healthcare plan questions, and questions about the employee handbook. Be brief in your answers.
Answer ONLY with the facts listed in the list of sources below. If there isn't enough information below, say you don't know. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question.
For tabular information return it as an html table. Do not return markdown format. If the question is not in English, answer in the language used in the question.
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brackets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].
{follow_up_questions_prompt}
{injected_prompt}
"""
    follow_up_questions_prompt_content = """Generate three very brief follow-up questions that the user would likely ask next about their healthcare plan and employee handbook.
Use double angle brackets to reference the questions, e.g. <<Are there exclusions for prescriptions?>>.
Try not to repeat questions that have already been asked.
Only generate questions and do not generate any text before or after the questions, such as 'Next Questions'"""

    query_prompt_template = """Below is a history of previous conversations and new questions from users that need to be searched and answered in the knowledge base about the company.
You have access to the Microsoft Search index, which contains over 100 documents.
Generate a search query based on the conversation and the new question.
Do not include the name of the cited file or document (e.g. info.txt or doc.pdf) in the search query term.
Only display search terms, do not output quotation marks, etc.
Do not include text in [] or <>> in search query terms.
Do not include special characters such as [].
If the question is not in English, generating the search query in the language used in the question.
If you cannot generate a search query, return only the number 0.
"""
    query_prompt_few_shots = [
        {"role": USER, "content": "私のヘルスプランについて教えてください。"},
        {"role": ASSISTANT, "content": "利用可能 ヘルスプラン"},
        {"role": USER, "content": "私のプランには有酸素運動は含まれていますか？"},
        {"role": ASSISTANT, "content": "ヘルスプラン 有酸素運動 適用範囲"},
    ]

    def __init__(
        self,
        openai_host: str,
        chatgpt_deployment: Optional[str],  # Not needed for non-Azure OpenAI
        embedding_deployment: Optional[str],  # Not needed for non-Azure OpenAI
        chatgpt_model: str,
        ai_search_endpoint: str,
        ai_search_index_name: str,
    ):
        self.openai_host = openai_host
        self.chatgpt_deployment = chatgpt_deployment
        self.embedding_deployment = embedding_deployment
        self.chatgpt_model = chatgpt_model
        self.chatgpt_token_limit = get_token_limit(chatgpt_model)
        self.ai_search_endpoint = ai_search_endpoint
        self.ai_search_index_name = ai_search_index_name

    async def run_without_streaming(
        self,
        history: list[dict[str, str]],
        overrides: dict[str, Any],
        obo_token,
        session_state: Any = None,
    ) -> dict[str, Any]:
        chat_resp = await self.run_ai_search_chat(
            history, obo_token
        )
        return chat_resp

    async def run_with_streaming(
        self,
        history: list[dict[str, str]],
        overrides: dict[str, Any],
        obo_token,
        session_state: Any = None,
    ) -> AsyncGenerator[dict, None]:
        extra_info, chat_coroutine = await self.run_simple_chat(
            history, overrides, should_stream=True
        )
        yield {
            "choices": [
                {
                    "delta": {"role": self.ASSISTANT},
                    "context": extra_info,
                    "session_state": session_state,
                    "finish_reason": None,
                    "index": 0,
                }
            ],
            "object": "chat.completion.chunk",
        }

        async for event in await chat_coroutine:
            # "2023-07-01-preview" API version has a bug where first response has empty choices
            if event["choices"]:
                yield event

    async def run(
        self, messages: list[dict], stream: bool = False, session_state: Any = None, context: dict[str, Any] = {}
    ) -> Union[dict[str, Any], AsyncGenerator[dict[str, Any], None]]:
        overrides = context.get("overrides", {})
        obo_token = context.get("obo_token", {})
        if stream is False:
            response = await self.run_without_streaming(messages, overrides, obo_token, session_state)
            return response
        else:
            return self.run_with_streaming(messages, overrides, obo_token, session_state)

    def get_messages_from_history(
        self,
        system_prompt: str,
        model_id: str,
        history: list[dict[str, str]],
        user_content: str,
        max_tokens: int,
        few_shots=[],
    ) -> list:
        message_builder = MessageBuilder(system_prompt, model_id)

        # Add examples to show the chat what responses we want. It will try to mimic any responses and make sure they match the rules laid out in the system message.
        for shot in few_shots:
            message_builder.append_message(shot.get("role"), shot.get("content"))

        append_index = len(few_shots) + 1

        message_builder.append_message(self.USER, user_content, index=append_index)
        total_token_count = message_builder.count_tokens_for_message(message_builder.messages[-1])

        newest_to_oldest = list(reversed(history[:-1]))
        for message in newest_to_oldest:
            potential_message_count = message_builder.count_tokens_for_message(message)
            if (total_token_count + potential_message_count) > max_tokens:
                logging.debug("Reached max tokens of %d, history will be truncated", max_tokens)
                break
            message_builder.append_message(message["role"], message["content"], index=append_index)
            total_token_count += potential_message_count
        return message_builder.messages

    def get_search_query(self, chat_completion: dict[str, Any], user_query: str):
        response_message = chat_completion["choices"][0]["message"]
        if function_call := response_message.get("function_call"):
            if function_call["name"] == "search_sources":
                arg = json.loads(function_call["arguments"])
                search_query = arg.get("search_query", self.NO_RESPONSE)
                if search_query != self.NO_RESPONSE:
                    return search_query
        elif query_text := response_message.get("content"):
            if query_text.strip() != self.NO_RESPONSE:
                return query_text
        return user_query
    
    async def run_ai_search_chat(
        self,
        history: list[dict[str, str]],
        obo_token,
        should_stream: bool = False,
    ) -> tuple:
        # Step 1: Generate embedding from user input
        user_input = history[-1]["content"]
        input_embedding = await self.__embed_text(user_input)

        # Step 2: Vector search using the embedding
        # TODO: ハイブリッド検索を行う
        search_results = self.__perform_vector_search(input_embedding)

        # TODO: 取り急ぎ、最初の検索結果のコンテンツを取得するが、
        # 複数のコンテンツがある場合に最も類似度が高いものを選択するように変更する
        src_content = search_results[0]["chunk"]

        # Step 4: Generate answer using citation sources
        chat_coroutine = await self.__answer_using_document(src_content, history, should_stream)
        return chat_coroutine.to_json()
    
    async def __embed_text(self, text: str):
        embedding_response = aoai_client.embeddings.create(
            input=text,
            model=self.embedding_deployment,
        )
        embedded_vector = embedding_response.data[0].embedding
        return embedded_vector

    def __perform_vector_search(self, input_embedding: float):
        AZURE_AI_SEARCH_API_KEY = os.getenv("AZURE_AI_SEARCH_API_KEY")
        key_credential = AzureKeyCredential(AZURE_AI_SEARCH_API_KEY)
        aisearch_client = SearchClient(
            endpoint=self.ai_search_endpoint,
            index_name=self.ai_search_index_name,
            credential=key_credential
        )

        vector = VectorizedQuery(
            vector=input_embedding,
            k_nearest_neighbors=3, 
            fields="text_vector",
        )
        item_paged = aisearch_client.search(
            vector_queries=[vector],
            search_text="*",
            top=3,
            select=["drive_id", "site_id", "item_id", "hit_id", "web_url", "chunk"],
        )
        results: list[dict] = []
        for item in item_paged:
            results.append(item)
        return results
    
    async def __answer_using_document(self, src_content: str, history: list[dict[str, str]], should_stream: bool = False):
        original_user_query = history[-1]["content"]
        response_token_limit = 1024
        messages_token_limit = self.chatgpt_token_limit - response_token_limit
        answer_messages = self.get_messages_from_history(
            system_prompt=self.system_message_chat_conversation,
            model_id=self.chatgpt_model,
            history=history,
            user_content=original_user_query + "\n\nSources:\n" + src_content,
            max_tokens=messages_token_limit,
        )

        # chat_coroutine = aoai_client.responses.create(
        completion = aoai_client.chat.completions.create(
            model=self.chatgpt_model,
            messages=answer_messages,
            temperature=0,
            max_tokens=response_token_limit,
            n=1,
            stream=should_stream
        )

        return completion
