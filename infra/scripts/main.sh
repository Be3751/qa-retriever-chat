#!/bin/bash

RANDOM_SUFFIX="6j8b0"
RESOURCE_GROUP="qachat-rg-$RANDOM_SUFFIX"
AI_SEARCH_NAME="qachat-ais-$RANDOM_SUFFIX"
OPENAI_SERVICE_NAME="qachat-aoai-$RANDOM_SUFFIX"
APP_SERVICE_PLAN_NAME="qachat-asp-$RANDOM_SUFFIX"
APP_SERVICE_NAME="qachat-as-$RANDOM_SUFFIX"

LOCATION="japaneast"
VNET_NAME="qachat-vn-$RANDOM_SUFFIX"
SUBNET_NAME="qachat-sbn-$RANDOM_SUFFIX"
SUBNET_PREFIX="10.0.5.0/24"
VM_NAME="qachat-temp-vm-$RANDOM_SUFFIX"
VM_IMAGE="Ubuntu2204"
ADMIN_USERNAME="azureuser"
SSH_KEY_PATH="$HOME/.ssh/id_rsa.pub"

# Step 1: App creation
echo "Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

echo "Creating Azure AI Search service..."
az search service create \
  --name $AI_SEARCH_NAME \
  --resource-group $RESOURCE_GROUP \
  --sku Basic \
  --location $LOCATION

echo "Creating Azure OpenAI service..."
az cognitiveservices account create \
  --name $OPENAI_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --kind OpenAI \
  --sku S0 \
  --location $LOCATION

echo "Deploying models for Chat..."
az cognitiveservices account deployment create \
  --name $OPENAI_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --deployment-name "gpt-4o" \
  --model-format OpenAI \
  --model-name "gpt-4o" \
  --model-version "2024-11-20"

az cognitiveservices account deployment create \
  --name $OPENAI_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --deployment-name "gpt-4o2" \
  --model-format OpenAI \
  --model-name "gpt-4o" \
  --model-version "2024-11-20"

echo "Deploying models for Embedding..."
az cognitiveservices account deployment create \
  --name $OPENAI_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --deployment-name "text-embedding-3-large" \
  --model-name "text-embedding-3-large" \
  --model-format OpenAI \
  --model-version "1"

az cognitiveservices account deployment create \
  --name $OPENAI_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --deployment-name "text-embedding-3-large2" \
  --model-name "text-embedding-3-large" \
  --model-format OpenAI \
  --model-version "1"

echo "Creating App Service Plan..."
az appservice plan create \
  --name $APP_SERVICE_PLAN_NAME \
  --resource-group $RESOURCE_GROUP \
  --sku B1 \
  --is-linux

echo "Creating App Service..."
az webapp create \
  --name $APP_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN_NAME \
  --runtime "PYTHON|3.11"

# Step 2: App configuration
echo "Configuring App Service..."
az webapp config appsettings set \
  --name $APP_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings "AZURE_OPENAI_SERVICE=$OPENAI_SERVICE_NAME" \
             "AZURE_AI_SEARCH_NAME=$AI_SEARCH_NAME"

echo "Enabling RBAC for Azure AI Search..."
az search service update \
  --name $AI_SEARCH_NAME \
  --resource-group $RESOURCE_GROUP \
  --set auth_options=null --disable-local-auth

# Get the Subscription ID
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "Subscription ID: $SUBSCRIPTION_ID"

# Get the Principal ID of the account logged in
YOUR_PRINCIPAL_ID=$(az ad signed-in-user show --query id -o tsv)
echo "Your Principal ID: $YOUR_PRINCIPAL_ID"

echo "Assigning roles to the logged-in user..."
az role assignment create \
  --assignee $YOUR_PRINCIPAL_ID \
  --role "Cognitive Services OpenAI Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$OPENAI_SERVICE_NAME"

az role assignment create \
  --assignee $YOUR_PRINCIPAL_ID \
  --role "Search Index Data Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Search/searchServices/$AI_SEARCH_NAME"

echo "Enabling system-assigned identity for App Service..."
az webapp identity assign \
  --name $APP_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP

APP_SERVICE_PRINCIPAL_ID=$(az webapp show \
  --name $APP_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --query identity.principalId -o tsv)
echo "App Service Principal ID: $APP_SERVICE_PRINCIPAL_ID"

echo "Assigning roles to the App Service..."
az role assignment create \
  --assignee $APP_SERVICE_PRINCIPAL_ID \
  --role "Cognitive Services OpenAI Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$OPENAI_SERVICE_NAME"

az role assignment create \
  --assignee $APP_SERVICE_PRINCIPAL_ID \
  --role "Search Index Data Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Search/searchServices/$AI_SEARCH_NAME"

# Step 3: Network isolation
echo "Creating virtual network..."
az network vnet create \
  --resource-group $RESOURCE_GROUP \
  --name $VNET_NAME \
  --address-prefix "10.0.0.0/16"

echo "Creating subnet..."
az network vnet subnet create \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $SUBNET_NAME \
  --address-prefix $SUBNET_PREFIX

echo "Integrating App Service with virtual network..."
az webapp vnet-integration add \
  --name $APP_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --vnet $VNET_NAME \
  --subnet $SUBNET_NAME

echo "Disabling public access to AI Search..."
az search service update \
  --name $AI_SEARCH_NAME \
  --resource-group $RESOURCE_GROUP \
  --public-network-access disabled

echo "Disabling public access to OpenAI Service..."
az cognitiveservices account update \
  --name $OPENAI_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --api-properties '{"publicNetworkAccess": "Disabled"}'

echo "Disabling public access to App Service..."
az webapp update \
  --name $APP_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --set publicNetworkAccess=Disabled

echo "Creating additional subnets for private endpoints..."
APP_SERVICE_SUBNET_NAME="qachat-sbn-app-service-$RANDOM_SUFFIX"
OPENAI_SERVICE_SUBNET_NAME="qachat-sbn-openai-service-$RANDOM_SUFFIX"
AI_SEARCH_SUBNET_NAME="qachat-sbn-ai-search-$RANDOM_SUFFIX"
APP_SERVICE_VNET_INTEG_SUBNET_NAME="qachat-sbn-app-service-vnet-integ-$RANDOM_SUFFIX"

az network vnet subnet create \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $AI_SEARCH_SUBNET_NAME \
  --address-prefix 10.0.0.0/24

az network vnet subnet create \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $OPENAI_SERVICE_SUBNET_NAME \
  --address-prefix 10.0.1.0/24

az network vnet subnet create \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $APP_SERVICE_SUBNET_NAME \
  --address-prefix 10.0.2.0/24

az network vnet subnet create \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $APP_SERVICE_VNET_INTEG_SUBNET_NAME \
  --address-prefix 10.0.3.0/24

echo "Creating private endpoints..."
AI_SEARCH_PRIVATE_ENDPOINT_NAME="qachat-pe-ais-$RANDOM_SUFFIX"
OPENAI_SERVICE_PRIVATE_ENDPOINT_NAME="qachat-pe-aoai-$RANDOM_SUFFIX"
APP_SERVICE_PRIVATE_ENDPOINT_NAME="qachat-pe-as-$RANDOM_SUFFIX"

az network private-endpoint create \
  --name $AI_SEARCH_PRIVATE_ENDPOINT_NAME \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --subnet $AI_SEARCH_SUBNET_NAME \
  --private-connection-resource-id "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Search/searchServices/$AI_SEARCH_NAME" \
  --group-id searchService \
  --connection-name "${AI_SEARCH_NAME}-connection"

az network private-endpoint create \
  --name $OPENAI_SERVICE_PRIVATE_ENDPOINT_NAME \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --subnet $OPENAI_SERVICE_SUBNET_NAME \
  --private-connection-resource-id "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$OPENAI_SERVICE_NAME" \
  --group-id account \
  --connection-name "${OPENAI_SERVICE_NAME}-connection"

az network private-endpoint create \
  --name $APP_SERVICE_PRIVATE_ENDPOINT_NAME \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --subnet $APP_SERVICE_SUBNET_NAME \
  --private-connection-resource-id "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$APP_SERVICE_NAME" \
  --group-id sites \
  --connection-name "${APP_SERVICE_NAME}-connection"

echo "Creating private DNS zones..."
az network private-dns zone create \
  --resource-group $RESOURCE_GROUP \
  --name "privatelink.search.windows.net"

az network private-dns zone create \
  --resource-group $RESOURCE_GROUP \
  --name "privatelink.azure.com"

az network private-dns zone create \
  --resource-group $RESOURCE_GROUP \
  --name "privatelink.azurewebsites.net"

echo "Linking private DNS zones to the virtual network..."
az network private-dns link vnet create \
  --resource-group $RESOURCE_GROUP \
  --zone-name "privatelink.search.windows.net" \
  --name "privatelink-search-windows-net" \
  --virtual-network $VNET_NAME \
  --registration-enabled false

az network private-dns link vnet create \
  --resource-group $RESOURCE_GROUP \
  --zone-name "privatelink.azure.com" \
  --name "privatelink-azure-com" \
  --virtual-network $VNET_NAME \
  --registration-enabled false

az network private-dns link vnet create \
  --resource-group $RESOURCE_GROUP \
  --zone-name "privatelink.azurewebsites.net" \
  --name "privatelink-azurewebsites-net" \
  --virtual-network $VNET_NAME \
  --registration-enabled false

echo "Creating private DNS A records..."
AI_SEARCH_PRIVATE_IP=$(az network private-endpoint show \
  --name $AI_SEARCH_PRIVATE_ENDPOINT_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "customDnsConfigs[0].ipAddresses[0]" -o tsv)

az network private-dns record-set a add-record \
  --resource-group $RESOURCE_GROUP \
  --zone-name "privatelink.search.windows.net" \
  --record-set-name $AI_SEARCH_NAME \
  --ipv4-address $AI_SEARCH_PRIVATE_IP

OPENAI_SERVICE_PRIVATE_IP=$(az network private-endpoint show \
  --name $OPENAI_SERVICE_PRIVATE_ENDPOINT_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "customDnsConfigs[0].ipAddresses[0]" -o tsv)

az network private-dns record-set a add-record \
  --resource-group $RESOURCE_GROUP \
  --zone-name "privatelink.azure.com" \
  --record-set-name $OPENAI_SERVICE_NAME \
  --ipv4-address $OPENAI_SERVICE_PRIVATE_IP

APP_SERVICE_PRIVATE_IP=$(az network private-endpoint show \
  --name $APP_SERVICE_PRIVATE_ENDPOINT_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "customDnsConfigs[0].ipAddresses[0]" -o tsv)

az network private-dns record-set a add-record \
  --resource-group $RESOURCE_GROUP \
  --zone-name "privatelink.azurewebsites.net" \
  --record-set-name $APP_SERVICE_NAME \
  --ipv4-address $APP_SERVICE_PRIVATE_IP

echo "Enabling VNet integration for App Service..."
az webapp vnet-integration add \
  --name $APP_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --vnet $VNET_NAME \
  --subnet $APP_SERVICE_VNET_INTEG_SUBNET_NAME
