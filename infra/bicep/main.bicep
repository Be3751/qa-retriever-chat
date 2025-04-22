param resourceGroupName string = 'fujitsu-test'
param location string = 'japaneast'
param subscriptionId string
param aiSearchName string
param openAiServiceName string
param appServiceName string

module networkModule './modules/network.bicep' = {
  name: 'networkDeployment'
  params: {
    resourceGroupName: resourceGroupName
    location: location
    subscriptionId: subscriptionId
    aiSearchName: aiSearchName
    openAiServiceName: openAiServiceName
  }
}

module appModule './modules/app.bicep' = {
  name: 'appDeployment'
  params: {
    resourceGroupName: resourceGroupName
    location: location
    appServiceName: appServiceName
    appServiceVnetIntegSubnetId: networkModule.outputs.appServiceVnetIntegSubnetId
  }
}
