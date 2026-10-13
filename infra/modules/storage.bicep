@description('Globally unique lowercase alphanumeric storage name.')
param name string

@description('Approved region.')
param location string

@description('Ownership and cost tags.')
param tags object

@description('Only the trusted broker receives ledger data-plane permissions.')
param brokerPrincipalId string

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: name
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    allowCrossTenantReplication: false
    publicNetworkAccess: 'Enabled'
    encryption: {
      keySource: 'Microsoft.Storage'
      services: {
        blob: {
          enabled: true
        }
      }
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

resource artifacts 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'artifacts'
  properties: {
    publicAccess: 'None'
  }
}

resource ledger 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'ledger'
  properties: {
    publicAccess: 'None'
  }
}

resource ledgerRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(ledger.id, brokerPrincipalId, 'ledger-data-contributor')
  scope: ledger
  properties: {
    principalId: brokerPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  }
}

output name string = storage.name
output accountUrl string = storage.properties.primaryEndpoints.blob
output artifactContainer string = artifacts.name
output ledgerContainer string = ledger.name
