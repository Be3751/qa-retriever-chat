import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI, RateLimitError
from dotenv import load_dotenv

from modules.record import Record

load_dotenv()
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT_URL")
deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
deployment2 = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT2")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    'https://cognitiveservices.azure.com/.default',
)
client = AzureOpenAI(
    azure_endpoint=endpoint,
    # azure_ad_token_provider=token_provider, 
    api_key=os.getenv("AZURE_OPENAI_API_KEY"), # マネージド ID 認証が失敗する場合はこちらのコメントアウトを解除して DefaultAzureCredentialを使用する引数をコメントアウト
    api_version=api_version,
)

with open('indexing/prompts_txt/for_comments_and_work_notes.txt', 'r') as f:
    sys_prompt_comments_and_work_notes = f.read()

with open('indexing/prompts_txt/for_description.txt', 'r') as f:
    sys_prompt_description = f.read()

def send_chat_completion(system_prompt: str, user_prompt: str)-> str:
    chat_prompt = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": system_prompt
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": user_prompt
                }
            ]
        }
    ]

    messages = chat_prompt
    attempt = 0
    deployments = [deployment, deployment2]
    current_deployment_index = 0

    # Infinite retries until successful completion
    while True:
        try:
            completion = client.chat.completions.create(
                model=deployments[current_deployment_index],
                messages=messages,
                max_completion_tokens=4096,
                temperature=0.7,
                top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0,
                stop=None,
                stream=False
            )
            return completion.choices[0].message.content
        except RateLimitError as e:
            print(f"Rate limit exceeded on model {deployments[current_deployment_index]}, switching to next model... (Attempt {attempt + 1})")
            current_deployment_index = (current_deployment_index + 1) % len(deployments)
            attempt += 1
        except Exception as e:
            print(f"Error occurred: {e}. User prompt: {user_prompt}")
            return "SKIPPED"

def cleanse_record(record: Record)-> dict:
    response_description = send_chat_completion(
        system_prompt=sys_prompt_description,
        user_prompt=record.description
    )
    
    response_comments_and_work_notes = send_chat_completion(
        system_prompt=sys_prompt_comments_and_work_notes,
        user_prompt=record.comments_and_work_notes
    )
    
    updated_record = record
    updated_record.description = response_description
    updated_record.comments_and_work_notes = response_comments_and_work_notes
    return updated_record