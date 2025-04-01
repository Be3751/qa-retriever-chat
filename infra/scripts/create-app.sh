RANDOM_SUFFIX="6j8b0"
RESOURCE_GROUP="qachat-rg-$RANDOM_SUFFIX"
AI_SEARCH_NAME="qachat-ais-$RANDOM_SUFFIX"
OPENAI_SERVICE_NAME="qachat-aoai-$RANDOM_SUFFIX"
APP_SERVICE_PLAN_NAME="qachat-asp-$RANDOM_SUFFIX"
APP_SERVICE_NAME="qachat-as-$RANDOM_SUFFIX"

# Create a resource group
az group create --name $RESOURCE_GROUP --location japaneast

# Create an AI Search
az search service create --name $AI_SEARCH_NAME --resource-group $RESOURCE_GROUP --sku Basic --location japaneast
# Create an OpenAI Service account
az cognitiveservices account create --name $OPENAI_SERVICE_NAME --resource-group $RESOURCE_GROUP --kind OpenAI --sku S0 
# Deploy two models for Chat
az cognitiveservices account deployment create --name $OPENAI_SERVICE_NAME --resource-group $RESOURCE_GROUP --deployment-name "gpt-4o" --model-format OpenAI --model-name "gpt-4o" --model-version "2024-11-20"
az cognitiveservices account deployment create --name $OPENAI_SERVICE_NAME --resource-group $RESOURCE_GROUP --deployment-name "gpt-4o2" --model-format OpenAI --model-name "gpt-4o" --model-version "2024-11-20"
# Deploy two models for Embedding
az cognitiveservices account deployment create --name $OPENAI_SERVICE_NAME --resource-group $RESOURCE_GROUP --deployment-name "text-embedding-3-large" --model-name "text-embedding-3-large" --model-format OpenAI --model-version "1"
az cognitiveservices account deployment create --name $OPENAI_SERVICE_NAME --resource-group $RESOURCE_GROUP --deployment-name "text-embedding-3-large2" --model-name "text-embedding-3-large" --model-format OpenAI --model-version "1"

# Create an App Service Plan
az appservice plan create --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP --sku B1 --is-linux
# Create an App Service 
az webapp create --resource-group $RESOURCE_GROUP --plan $APP_SERVICE_PLAN_NAME --name $APP_SERVICE_NAME --runtime "PYTHON|3.11"
