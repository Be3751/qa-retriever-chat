param resourceGroupName string
param location string
param appServiceName string
param appServiceVnetIntegSubnetId string

// App Service Plan
resource appServicePlan 'Microsoft.Web/serverfarms@2021-02-01' = {
  name: '${appServiceName}-plan'
  location: location
  sku: {
    name: 'P1v2'
    tier: 'PremiumV2'
    size: 'P1v2'
    capacity: 1
  }
  properties: {
    reserved: false
  }
}

// App Service
resource appService 'Microsoft.Web/sites@2021-02-01' = {
  name: appServiceName
  location: location
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      vnetRouteAllEnabled: true
    }
  }
}

// VNet Integration for App Service
resource appServiceVnetIntegration 'Microsoft.Web/sites/networkConfig@2021-02-01' = {
  parent: appService
  name: 'virtualNetwork'
  properties: {
    subnetResourceId: appServiceVnetIntegSubnetId
  }
}

// Disable Public Access for App Service
resource appServiceAccessRestrictions 'Microsoft.Web/sites/config@2021-02-01' = {
  parent: appService
  name: 'web'
  properties: {
    ipSecurityRestrictions: [
      {
        ipAddress: '0.0.0.0/0'
        action: 'Deny'
        priority: 100
        name: 'DenyAll'
        description: 'Deny all public access'
      }
    ]
  }
}
