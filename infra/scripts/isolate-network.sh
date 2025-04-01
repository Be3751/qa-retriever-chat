RANDOM_SUFFIX="6j8b0"
RESOURCE_GROUP="qachat-rg-$RANDOM_SUFFIX"
AI_SEARCH_NAME="qachat-ais-$RANDOM_SUFFIX"
OPENAI_SERVICE_NAME="qachat-aoai-$RANDOM_SUFFIX"
APP_SERVICE_NAME="qachat-as-$RANDOM_SUFFIX"

VNET_NAME="qachat-vn-$RANDOM_SUFFIX"
APP_SERVICE_SUBNET_NAME="qachat-sbn-app-service-$RANDOM_SUFFIX"
OPENAI_SERVICE_SUBNET_NAME="qachat-sbn-openai-service-$RANDOM_SUFFIX"
AI_SEARCH_SUBNET_NAME="qachat-sbn-ai-search-$RANDOM_SUFFIX"
APP_SERVICE_VNET_INTEG_SUBNET_NAME="qachat-sbn-app-service-vnet-integ-$RANDOM_SUFFIX"

# Disable public access to AI Search
az search service update --name $AI_SEARCH_NAME --resource-group $RESOURCE_GROUP --public-network-access disabled
# Disable public access to OpenAI Service
az cognitiveservices account update --name $OPENAI_SERVICE_NAME --resource-group $RESOURCE_GROUP --api-properties '{"publicNetworkAccess": "Disabled"}'
# Disable public access to App Service
az webapp update --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP --set publicNetworkAccess=Disabled

# Create a Virtual Network
az network vnet create --resource-group $RESOURCE_GROUP --name $VNET_NAME --address-prefix 10.0.0.0/16 --location japaneast
# Create a Subnet for Private Endpoints to AI Search, OpenAI Service, and App Service
az network vnet subnet create --resource-group $RESOURCE_GROUP --vnet-name $VNET_NAME --name $AI_SEARCH_SUBNET_NAME --address-prefix 10.0.0.0/24
az network vnet subnet create --resource-group $RESOURCE_GROUP --vnet-name $VNET_NAME --name $OPENAI_SERVICE_SUBNET_NAME --address-prefix 10.0.1.0/24
az network vnet subnet create --resource-group $RESOURCE_GROUP --vnet-name $VNET_NAME --name $APP_SERVICE_SUBNET_NAME --address-prefix 10.0.2.0/24
# Create a Subnet for VNet Integration of App Service
az network vnet subnet create --resource-group $RESOURCE_GROUP --vnet-name $VNET_NAME --name $APP_SERVICE_VNET_INTEG_SUBNET_NAME --address-prefix 10.0.3.0/24

AI_SEARCH_PRIVATE_ENDPOINT_NAME="qachat-pe-ais-$RANDOM_SUFFIX"
OPENAI_SERVICE_PRIVATE_ENDPOINT_NAME="qachat-pe-aoai-$RANDOM_SUFFIX"
APP_SERVICE_PRIVATE_ENDPOINT_NAME="qachat-pe-as-$RANDOM_SUFFIX"

# Create a Private Endpoint for AI Search
az network private-endpoint create --name $AI_SEARCH_PRIVATE_ENDPOINT_NAME --resource-group $RESOURCE_GROUP --vnet-name $VNET_NAME --subnet $AI_SEARCH_SUBNET_NAME --private-connection-resource-id "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Search/searchServices/$AI_SEARCH_NAME" --group-id searchService --connection-name "${AI_SEARCH_NAME}-connection"
# NOTE! Run the following command after giving a custom sub domain name to OpenAI Service on Azure Portal
# Create a Private Endpoint for OpenAI Service
az network private-endpoint create --name $OPENAI_SERVICE_PRIVATE_ENDPOINT_NAME --resource-group $RESOURCE_GROUP --vnet-name $VNET_NAME --subnet $OPENAI_SERVICE_SUBNET_NAME --private-connection-resource-id "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$OPENAI_SERVICE_NAME" --group-id account --connection-name "${OPENAI_SERVICE_NAME}-connection"
# Create a Private Endpoint for App Service
az network private-endpoint create --name $APP_SERVICE_PRIVATE_ENDPOINT_NAME --resource-group $RESOURCE_GROUP --vnet-name $VNET_NAME --subnet $APP_SERVICE_SUBNET_NAME --private-connection-resource-id "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$APP_SERVICE_NAME" --group-id sites --connection-name "${APP_SERVICE_NAME}-connection"

# Create a Private DNS Zone for AI Search, OpenAI Service, and App Service
az network private-dns zone create --resource-group $RESOURCE_GROUP --name "privatelink.search.windows.net"
az network private-dns zone create --resource-group $RESOURCE_GROUP --name "privatelink.azure.com"
az network private-dns zone create --resource-group $RESOURCE_GROUP --name "privatelink.azurewebsites.net"

# Link the Private DNS Zone to the Virtual Network
az network private-dns link vnet create --resource-group $RESOURCE_GROUP --zone-name "privatelink.search.windows.net" --name "privatelink-search-windows-net" --virtual-network $VNET_NAME --registration-enabled false
az network private-dns link vnet create --resource-group $RESOURCE_GROUP --zone-name "privatelink.azure.com" --name "privatelink-azure-com" --virtual-network $VNET_NAME --registration-enabled false
az network private-dns link vnet create --resource-group $RESOURCE_GROUP --zone-name "privatelink.azurewebsites.net" --name "privatelink-azurewebsites-net" --virtual-network $VNET_NAME --registration-enabled false

# Create a Private DNS A record for AI Search, OpenAI Service, and App Service
AI_SEARCH_PRIVATE_IP=$(az network private-endpoint show --name $AI_SEARCH_PRIVATE_ENDPOINT_NAME --resource-group $RESOURCE_GROUP --query "customDnsConfigs[0].ipAddresses[0]" -o tsv)
az network private-dns record-set a add-record --resource-group $RESOURCE_GROUP --zone-name "privatelink.search.windows.net" --record-set-name $AI_SEARCH_NAME --ipv4-address $AI_SEARCH_PRIVATE_IP
OPENAI_SERVICE_PRIVATE_IP=$(az network private-endpoint show --name $OPENAI_SERVICE_PRIVATE_ENDPOINT_NAME --resource-group $RESOURCE_GROUP --query "customDnsConfigs[0].ipAddresses[0]" -o tsv)
az network private-dns record-set a add-record --resource-group $RESOURCE_GROUP --zone-name "privatelink.azure.com" --record-set-name $OPENAI_SERVICE_NAME --ipv4-address $OPENAI_SERVICE_PRIVATE_IP
APP_SERVICE_PRIVATE_IP=$(az network private-endpoint show --name $APP_SERVICE_PRIVATE_ENDPOINT_NAME --resource-group $RESOURCE_GROUP --query "customDnsConfigs[0].ipAddresses[0]" -o tsv)
az network private-dns record-set a add-record --resource-group $RESOURCE_GROUP --zone-name "privatelink.azurewebsites.net" --record-set-name $APP_SERVICE_NAME --ipv4-address $APP_SERVICE_PRIVATE_IP

# Enable VNet Integration for App Service
az webapp vnet-integration add --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP --vnet $VNET_NAME --subnet $APP_SERVICE_VNET_INTEG_SUBNET_NAME
