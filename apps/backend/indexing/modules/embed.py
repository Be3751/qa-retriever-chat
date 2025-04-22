import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI, RateLimitError
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT_URL")  
deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
deployment2 = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT2")
api_key = os.getenv("AZURE_OPENAI_API_KEY", "REPLACE_WITH_YOUR_KEY_VALUE_HERE")  
api_version = os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION", "2023-05-15")
print(f"Using OpenAI endpoint: {endpoint}, deployment: {deployment}, deployment2: {deployment2}, api_version: {api_version}")

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    'https://cognitiveservices.azure.com/.default',
)

openai_client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=api_key, # マネージド ID 認証が失敗する場合はこちらのコメントアウトを解除して DefaultAzureCredentialを使用する引数をコメントアウト
    api_version=api_version,
    # azure_ad_token_provider=token_provider,
)

def embed_text(text: str) -> list[float]:
    attempt = 0
    deployments = [deployment, deployment2]
    current_deployment_index = 0

    while True:
        try:
            embedding_response = openai_client.embeddings.create(
                input=text,
                model=deployments[current_deployment_index],
            )
            return embedding_response.data[0].embedding
        except RateLimitError as e:
            print(f"Rate limit exceeded on model {deployments[current_deployment_index]}, switching to next model... (Attempt {attempt + 1})")
            current_deployment_index = (current_deployment_index + 1) % len(deployments)
            attempt += 1
        except Exception as e:
            print(f"Error occurred: {e}. Text: {text}")
            return []