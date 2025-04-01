RANDOM_SUFFIX="6j8b0"
RESOURCE_GROUP="qachat-rg-$RANDOM_SUFFIX"
AI_SEARCH_NAME="qachat-ais-$RANDOM_SUFFIX"
OPENAI_SERVICE_NAME="qachat-aoai-$RANDOM_SUFFIX"
APP_SERVICE_PLAN_NAME="qachat-asp-$RANDOM_SUFFIX"
APP_SERVICE_NAME="qachat-as-$RANDOM_SUFFIX"

# Make RBAC enabled
az search service update --name $AI_SEARCH_NAME --resource-group $RESOURCE_GROUP --set auth_options=null --disable-local-auth
# If you want to use make both RBAC and API Key access enabled, comment out the above line and uncomment the below line
# az search service update --name $AI_SEARCH_NAME --resource-group $RESOURCE_GROUP --set auth_options=null --aad-auth-failure-mode http401WithBearerChallenge --auth-options aadOrApiKey

# Get the Subscription ID
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo $SUBSCRIPTION_ID

# Get the Principal ID of the account logged in
YOUR_PRINCIPAL_ID=$(az ad signed-in-user show --query id -o tsv)
echo $YOUR_PRINCIPAL_ID

# Assign Cognitive Services OpenAI Contributor role to your account
az role assignment create --assignee $YOUR_PRINCIPAL_ID --role "Cognitive Services OpenAI Contributor" --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$OPENAI_SERVICE_NAME"
# Assign Search Index Data Contributor role to your account
az role assignment create --assignee $YOUR_PRINCIPAL_ID --role "Search Index Data Contributor" --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Search/searchServices/$AI_SEARCH_NAME"

# Make System assigned identity enabled for App Service
az webapp identity assign --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP
APP_SERVICE_PRINCIPAL_ID=$(az webapp show --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP --query identity.principalId -o tsv)
echo $APP_SERVICE_PRINCIPAL_ID

# Assign Cognitive Services OpenAI Contributor role to App Service
az role assignment create --assignee $APP_SERVICE_PRINCIPAL_ID --role "Cognitive Services OpenAI Contributor" --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$OPENAI_SERVICE_NAME"
# Assign Search Index Data Contributor role to App Service
az role assignment create --assignee $APP_SERVICE_PRINCIPAL_ID --role "Search Index Data Contributor" --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Search/searchServices/$AI_SEARCH_NAME"
