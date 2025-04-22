import os
import hashlib

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import (
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
    VectorSearchProfile,
    SearchIndex,
    VectorSearchAlgorithmKind
)
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from dotenv import load_dotenv

from modules.record import Record
from modules.embed import embed_text

load_dotenv()
AZURE_AI_SEARCH_ENDPOINT = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
AZURE_AI_SEARCH_INDEX_NAME = os.getenv("AZURE_AI_SEARCH_INDEX_NAME")
AZURE_AI_SEARCH_API_KEY = os.getenv("AZURE_AI_SEARCH_API_KEY")

credential = DefaultAzureCredential()
key_credential = AzureKeyCredential(AZURE_AI_SEARCH_API_KEY) # マネージド ID 認証が失敗する場合はこちらのコメントアウトを解除して DefaultAzureCredentialを使用する引数をコメントアウト

search_index_client = SearchIndexClient(
    endpoint=AZURE_AI_SEARCH_ENDPOINT, 
    credential=key_credential # マネージド ID 認証が失敗する場合はこちらのコメントアウトを解除して DefaultAzureCredentialを使用する引数をコメントアウト
    # credential=credential
)
search_client = SearchClient(
    endpoint=AZURE_AI_SEARCH_ENDPOINT,
    index_name=AZURE_AI_SEARCH_INDEX_NAME,
    credential=key_credential # マネージド ID 認証が失敗する場合はこちらのコメントアウトを解除して DefaultAzureCredentialを使用する引数をコメントアウト
    # credential=credential
)

def initialize_index():
    try:
        # Check if the index already exists
        existing_index = search_index_client.get_index(AZURE_AI_SEARCH_INDEX_NAME)
        if existing_index:
            raise Exception(f"Index \"{AZURE_AI_SEARCH_INDEX_NAME}\" already exists.")
    except Exception as e:
        if "No index" not in str(e):
            raise Exception(f"Error occurs if index exists: {e}")

    fields = [
        SearchField(name="id", type=SearchFieldDataType.String, key=True),
        SearchField(name="question", type=SearchFieldDataType.String, searchable=True),
        SearchField(name="answer", type=SearchFieldDataType.String, searchable=True),
        SearchField(name="services", type=SearchFieldDataType.Collection(SearchFieldDataType.String), searchable=True, filterable=True, facetable=True),
        SearchField(name="tag", type=SearchFieldDataType.Collection(SearchFieldDataType.String), searchable=True, filterable=True, facetable=True),
        SearchField(
            name="question_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=3072,
            vector_search_profile_name="myProfile",
        ),
        SearchField(
            name="answer_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=3072,
            vector_search_profile_name="myProfile",
        ),
    ]

    profile = VectorSearchProfile(
        name="myProfile",
        algorithm_configuration_name="myHnsw",
    )
    algorithm = VectorSearchAlgorithmConfiguration(
        name="myHnsw",
    )
    algorithm.kind = VectorSearchAlgorithmKind.HNSW

    vector_search = VectorSearch(profiles=[profile], algorithms=[algorithm])
    index = SearchIndex(name=AZURE_AI_SEARCH_INDEX_NAME, fields=fields, vector_search=vector_search)

    search_index_client.create_or_update_index(index)

def check_index_exists() -> bool:
    try:
        search_index_client.get_index(AZURE_AI_SEARCH_INDEX_NAME)
        print(f"Index \"{AZURE_AI_SEARCH_INDEX_NAME}\" exists.")
        return True
    except Exception as e:
        if isinstance(e, ResourceNotFoundError):
            return False
        else:
            raise Exception(f"Error checking if index exists: {e}")

def check_document_exists(record: Record) -> bool:
    document_id = generate_document_key(record)
    try:
        document = search_client.get_document(key=document_id)
        if document:
            return True
    except Exception as e:
        if isinstance(e, ResourceNotFoundError):
            return False
        else:
            raise Exception(f"Error checking if document exists: {e}")

def generate_document_key(record: Record) -> str:
    unique_string = record.description + record.comments_and_work_notes + ''.join([record.service, record.service2, record.service3])
    return hashlib.md5(unique_string.encode()).hexdigest()

def create_document_from_record(record: Record) -> dict:
    question_vector = embed_text(record.description)
    answer_vector = embed_text(record.comments_and_work_notes)
    
    document_id = generate_document_key(record)

    return {
        "id": document_id,
        "question": record.description,
        "answer": record.comments_and_work_notes,
        "services": [record.service, record.service2, record.service3], 
        "tag": record.tag.split(','),
        "question_vector": question_vector,
        "answer_vector": answer_vector,
    }

def upload_documents(records: list[Record]) -> None:
    search_client.upload_documents(records)
