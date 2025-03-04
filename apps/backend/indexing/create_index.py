import os
import json

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import (
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
    VectorSearchProfile,
    SearchIndex
)
import openai
import uuid

credential = DefaultAzureCredential()

load_dotenv()
AZURE_AI_SEARCH_ENDPOINT = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
AZURE_AI_SEARCH_INDEX_NAME = os.getenv("AZURE_AI_SEARCH_INDEX_NAME")
AZURE_OPENAI_ACCOUNT = os.getenv("AZURE_OPENAI_ACCOUNT")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
print(f"Creating search index \"{AZURE_AI_SEARCH_INDEX_NAME}\" in \"{AZURE_AI_SEARCH_ENDPOINT}\"")
print(f"Using OpenAI account \"{AZURE_OPENAI_ACCOUNT}\" and deployment \"{AZURE_OPENAI_EMBEDDING_DEPLOYMENT}\"")

# Create a search index  
index_client = SearchIndexClient(endpoint=AZURE_AI_SEARCH_ENDPOINT, credential=credential)  

# Delete the search index if it exists
try:
    index_client.delete_index(AZURE_AI_SEARCH_INDEX_NAME)
    print(f"Deleted existing index \"{AZURE_AI_SEARCH_INDEX_NAME}\"")
except Exception as e:
    print(f"Index \"{AZURE_AI_SEARCH_INDEX_NAME}\" does not exist or could not be deleted: {e}")

fields = [
    SearchField(name="id", type=SearchFieldDataType.String, key=True),
    SearchField(name="drive_id", type=SearchFieldDataType.String),
    SearchField(name="site_id", type=SearchFieldDataType.String),
    SearchField(name="item_id", type=SearchFieldDataType.String),
    SearchField(name="hit_id", type=SearchFieldDataType.String),
    SearchField(name="web_url", type=SearchFieldDataType.String),
    SearchField(name="chunk", type=SearchFieldDataType.String, sortable=False, filterable=False, facetable=False, analyzer_name="ja.microsoft"),
    SearchField(
        name="text_vector",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,
        vector_search_dimensions=1536,
        vector_search_profile_name="myProfile",
    ),
]

# Create the search index
from azure.search.documents.indexes.models import VectorSearchAlgorithmKind

profile = VectorSearchProfile(
    name="myProfile",
    algorithm_configuration_name="myHnsw",
)
algorithm = VectorSearchAlgorithmConfiguration(
    name="myHnsw",
)
# kind property might be insertable once the instance is created
algorithm.kind = VectorSearchAlgorithmKind.HNSW

vector_search = VectorSearch( profiles=[profile], algorithms=[algorithm])
index = SearchIndex(name=AZURE_AI_SEARCH_INDEX_NAME, fields=fields, vector_search=vector_search)
result = index_client.create_or_update_index(index)

# Upload documents to the search index
markdown_directory = os.path.join(os.path.dirname(__file__), "files", "markdown")
documents = []
file_info_path = os.path.join(os.path.dirname(__file__), "file_info.json")
with open(file_info_path, 'r', encoding='utf-8') as file_info_file:
    file_info_list = json.load(file_info_file)

CHUNK_SIZE = 500
for file_info in file_info_list:
    print("Processing file:", file_info["file_name"])
    file_name_without_ext = os.path.splitext(file_info["file_name"])[0]
    file_path = os.path.join(markdown_directory, f"{file_name_without_ext}.md")
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            chunks = [content[i:i+CHUNK_SIZE] for i in range(0, len(content), CHUNK_SIZE)]
            for idx, chunk in enumerate(chunks):
                chatgpt_args = {"deployment_id": AZURE_OPENAI_EMBEDDING_DEPLOYMENT}

                openai.api_type = "azure_ad"
                openai.api_base = AZURE_OPENAI_ACCOUNT
                openai.api_version = "2023-05-15"
                openai.api_key = credential.get_token("https://cognitiveservices.azure.com/.default").token

                embedding_response = openai.Embedding.create(
                    **chatgpt_args,
                    input=chunk,
                    model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT
                )
                embedding = embedding_response["data"][0]["embedding"]

                documents.append({
                    "id": str(uuid.uuid4()),
                    "drive_id": file_info["drive_id"],
                    "site_id": file_info["site_id"],
                    "item_id": file_info["item_id"],
                    "hit_id": file_info["hit_id"],
                    "web_url": file_info["web_url"],
                    "chunk": chunk,
                    "text_vector": embedding,
                })
    else:
        print(f"File not found: {file_path}")

search_client = SearchClient(
    endpoint=AZURE_AI_SEARCH_ENDPOINT,
    index_name=AZURE_AI_SEARCH_INDEX_NAME,
    credential=credential
)
search_client.upload_documents(documents)
print(f"Uploaded {len(documents)} chunked documents to index \"{AZURE_AI_SEARCH_INDEX_NAME}\"")
