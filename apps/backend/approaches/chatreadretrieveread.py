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
from sklearn.feature_extraction.text import TfidfVectorizer
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

dotenv.load_dotenv()

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    'https://cognitiveservices.azure.com/.default',
)
aoai_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT_URL"),
    azure_ad_token_provider=token_provider,
    # api_key=os.getenv("AZURE_OPENAI_API_KEY"), # マネージド ID 認証が失敗する場合はこちらのコメントアウトを解除して DefaultAzureCredentialを使用する引数をコメントアウト
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
)

class ChatReadRetrieveReadApproach(Approach):
    # Chat roles
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    NO_RESPONSE = "0"

    """
    Simple retrieve-then-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
    top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion
    (answer) with that prompt.
    """
    system_message_chat_conversation = """あなたは、カスタマーサポートのQ&Aの回答文を生成するエキスパートです。
                                    ■指示No.1:
                                    入力された質問に類似した質問とその回答を参考にして、ユーザーの質問に回答する文章を生成してください。

                                    ■指示No.2:
                                    参照情報源にない質問には、「その情報には対応していません」と明確に伝えてください。
                                    たとえば、以下のような回答を使用できます。
                                    「申し訳ありませんが、このシステムではその質問には対応できません。」
                                    「このシステムは指定された情報源に基づいて回答しますが、お探しの情報は含まれていないようです。」
                                    「該当情報は参照データ内に見つかりませんでした。他の手段でお調べください。」

                                    ■指示No.3:
                                    また、最新のステータスや個別の事情を確認する質問が入力された場合は、
                                    「最新状況についてはサポートチームにお問い合わせください。」と返答してください。
    """
    system_prompt_classification = """あなたは、カスタマーサポートのQ&Aの問い合わせ文を分析するエキスパートです。 
                                    Q&Aの担当者に対して、情報の提示を求める質問か、手続きを依頼するアクションの要求かを分類してください。
                                    アクションならtrue、情報の提示ならfalseです。出力値はtrueかfalseだけにしてください。"""

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
        # Step 1: Extract keywords from user input
        user_input = history[-1]["content"]
        keywords = self.__extract_keywords(user_input)

        # Step 2: Generate embedding from user input
        input_embedding = await self.__embed_text(user_input)

        # Step 3: Hybrid search using the input embedding
        search_results = self.__perform_hybrid_search(input_embedding, keywords)
        if len(search_results) == 0:
            return {
                "id": "0",
                "choices": [
                    {
                        "message": {
                            "role": self.ASSISTANT,
                            "content": "検索結果が見つかりませんでした。"
                        }
                    }
                ]
            }
        hit_existing_question = search_results[0]["question"]
        hit_existing_answer = search_results[0]["answer"]

        # Step 4: Generate answer using citation sources
        chat_coroutine = await self.__answer_using_document(
            hit_existing_question, 
            hit_existing_answer, 
            history, 
            should_stream)
        return chat_coroutine.to_json()

    def __extract_keywords(self, text: str) -> str:
        documents = [text]
        vectorizer = TfidfVectorizer()
        X = vectorizer.fit_transform(documents)
        words = vectorizer.get_feature_names_out()
        scores = X.toarray().flatten()
        important_words = [words[i] for i in scores.argsort()[-5:]]  # Top 5 words
        return " ".join(important_words)
    
    async def __embed_text(self, text: str):
        embedding_response = aoai_client.embeddings.create(
            input=text,
            model=self.embedding_deployment,
        )
        embedded_vector = embedding_response.data[0].embedding
        return embedded_vector

    def __perform_hybrid_search(self, input_embedding: float, search_text: str = "*"):
        AZURE_AI_SEARCH_API_KEY = os.getenv("AZURE_AI_SEARCH_API_KEY")
        key_credential = AzureKeyCredential(AZURE_AI_SEARCH_API_KEY)
        aisearch_client = SearchClient(
            endpoint=self.ai_search_endpoint,
            index_name=self.ai_search_index_name,
            # credential=DefaultAzureCredential(),
            credential=key_credential # マネージド ID 認証が失敗する場合はこちらのコメントアウトを解除して DefaultAzureCredentialを使用する引数をコメントアウト
        )

        k = 10
        question_vector = VectorizedQuery(
            vector=input_embedding,
            k_nearest_neighbors=k, 
            fields="question_vector",
        )
        answer_vector = VectorizedQuery(
            vector=input_embedding,
            k_nearest_neighbors=k, 
            fields="answer_vector",
        )
        # print("質問ベクトル:", question_vector)
        # print("回答ベクトル:", answer_vector)
        item_paged = aisearch_client.search(
            vector_queries=[question_vector, answer_vector],
            search_text=search_text,
            top=k,
        )
        results: list[dict] = []
        for item in item_paged:
            results.append(item)
        print("検索結果:", results)
        return results
    
    async def __answer_using_document(
            self,
            hit_existing_question: str,
            hit_existing_answer: str,
            history: list[dict[str, str]], 
            should_stream: bool = False):
        original_user_query = history[-1]["content"]
        user_content = "ユーザーの質問文: " + original_user_query + "\n\n類似した既存の質問: " + hit_existing_question + "\n\n類似した既存の質問に対する回答: " + hit_existing_answer
        response_token_limit = 4096
        messages_token_limit = self.chatgpt_token_limit - response_token_limit
        answer_messages = self.get_messages_from_history(
            system_prompt=self.system_message_chat_conversation,
            model_id=self.chatgpt_model,
            history=history,
            user_content=user_content,
            max_tokens=messages_token_limit,
        )

        completion = aoai_client.chat.completions.create(
            model=self.chatgpt_model,
            messages=answer_messages,
            temperature=0,
            max_tokens=response_token_limit,
            n=1,
            stream=should_stream
        )

        return completion
