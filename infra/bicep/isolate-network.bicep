param resourceGroupName string = 'fujitsu-test'
param location string = 'japaneast'
param vnetName string = 'fujitsu-vn-6j8b0'
param subscriptionId string
param aiSearchName string
param openAiServiceName string

// Virtual Network
resource vnet 'Microsoft.Network/virtualNetworks@2021-05-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/16'
      ]
    }
  }
}

// Subnets
resource aiSearchSubnet 'Microsoft.Network/virtualNetworks/subnets@2021-05-01' = {
  parent: vnet
  name: 'fujitsu-sbn-ai-search-6j8b0'
  properties: {
    addressPrefix: '10.0.0.0/24'
  }
}

resource openAiServiceSubnet 'Microsoft.Network/virtualNetworks/subnets@2021-05-01' = {
  parent: vnet
  name: 'fujitsu-sbn-openai-service-6j8b0'
  properties: {
    addressPrefix: '10.0.1.0/24'
  }
}

// Private Endpoints
resource aiSearchPrivateEndpoint 'Microsoft.Network/privateEndpoints@2021-05-01' = {
  name: 'fujitsu-pe-ais-6j8b0'
  location: location
  properties: {
    subnet: {
      id: aiSearchSubnet.id
    }
    privateLinkServiceConnections: [
      {
        name: '${aiSearchName}-connection'
        properties: {
          privateLinkServiceId: subscriptionResourceId('Microsoft.Search/searchServices', aiSearchName)
          groupIds: ['searchService']
        }
      }
    ]
  }
}

resource openAiServicePrivateEndpoint 'Microsoft.Network/privateEndpoints@2021-05-01' = {
  name: 'fujitsu-pe-aoai-6j8b0'
  location: location
  properties: {
    subnet: {
      id: openAiServiceSubnet.id
    }
    privateLinkServiceConnections: [
      {
        name: '${openAiServiceName}-connection'
        properties: {
          privateLinkServiceId: subscriptionResourceId('Microsoft.CognitiveServices/accounts', openAiServiceName)
          groupIds: ['account']
        }
      }
    ]
  }
}

// Private DNS Zones
resource searchDnsZone 'Microsoft.Network/privateDnsZones@2021-05-01' = {
  name: 'privatelink.search.windows.net'
  location: location
}

resource azureDnsZone 'Microsoft.Network/privateDnsZones@2021-05-01' = {
  name: 'privatelink.azure.com'
  location: location
}

// DNS Zone Links
resource searchDnsZoneLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2021-05-01' = {
  parent: searchDnsZone
  name: 'privatelink-search-windows-net'
  properties: {
    virtualNetwork: {
      id: vnet.id
    }
    registrationEnabled: false
  }
}

resource azureDnsZoneLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2021-05-01' = {
  parent: azureDnsZone
  name: 'privatelink-azure-com'
  properties: {
    virtualNetwork: {
      id: vnet.id
    }
    registrationEnabled: false
  }
}

// Disable Public Access for AI Search
resource aiSearchPublicAccess 'Microsoft.Search/searchServices@2021-04-01' = {
  name: aiSearchName
  location: location
  properties: {
    publicNetworkAccess: 'Disabled'
  }
}

// Disable Public Access for OpenAI Service
resource openAiServicePublicAccess 'Microsoft.CognitiveServices/accounts@2021-04-01' = {
  name: openAiServiceName
  location: location
  properties: {
    apiProperties: {
      publicNetworkAccess: 'Disabled'
    }
  }
}
