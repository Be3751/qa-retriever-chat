RANDOM_SUFFIX="6j8b0"
RESOURCE_GROUP="qachat-rg-$RANDOM_SUFFIX"
AI_SEARCH_NAME="qachat-ais-$RANDOM_SUFFIX"
OPENAI_SERVICE_NAME="qachat-aoai-$RANDOM_SUFFIX"
APP_SERVICE_NAME="qachat-as-$RANDOM_SUFFIX"

# NOTE! Replace the following values with your own values
AZURE_TENANT_ID="your-tenant-id" # Replace with your Azure tenant ID
AZURE_SERVER_APP_ID="your-server-app-id" # Replace with your application registration's application (client) ID
AZURE_CLIENT_APP_ID=$AZURE_SERVER_APP_ID
AZURE_SERVER_APP_SECRET="your-server-app-secret" # Replace with your application registration's client secret

# Set start-up command for the App Service
az webapp config set \
    --name $APP_SERVICE_NAME \
    --resource-group $RESOURCE_GROUP \
    --startup-file "python3 -m gunicorn main:app"

# Set environment variables for the App Service
az webapp config appsettings set \
    --name $APP_SERVICE_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings "SCM_DO_BUILD_DURING_DEPLOYMENT=true" \
    "TOKEN_CACHE_PATH=None" \
    "AZURE_OPENAI_SERVICE=$OPENAI_SERVICE_NAME" \
    "AZURE_OPENAI_CHATGPT_MODEL=gpt-4o" \
    "AZURE_OPENAI_CHATGPT_DEPLOYMENT=gpt-4o" \
    "AZURE_USE_AUTHENTICATION=true" \
    "AZURE_TENANT_ID=$AZURE_TENANT_ID" \
    "AZURE_SERVER_APP_ID=$AZURE_SERVER_APP_ID" \
    "AZURE_CLIENT_APP_ID=$AZURE_CLIENT_APP_ID" \
    "AZURE_SERVER_APP_SECRET=$AZURE_SERVER_APP_SECRET"