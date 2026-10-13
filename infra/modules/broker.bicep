@description('Broker app name, below the conservative 32-character limit.')
param name string
@description('Dedicated environment name.')
param environmentName string
@description('Approved region.')
param location string
@description('Ownership tags.')
param tags object
@description('Broker-only user-assigned identity resource ID.')
param identityId string
@description('Broker-only identity client ID.')
param identityClientId string
@description('Pinned broker image.')
param image string
@description('Secret used only by trusted operator and broker to sign run credentials.')
@secure()
param signingSecret string
@description('HTTPS Blob endpoint.')
param storageAccountUrl string
@description('Private broker ledger container.')
param ledgerContainer string
@description('Approved model endpoint.')
param modelEndpoint string
@description('Bound deployment.')
param modelDeployment string
@description('Verified API version.')
param modelApiVersion string
@description('Frozen model version.')
param modelVersion string
@description('Frozen model family name.')
param modelName string
@description('Input price per million tokens.')
param inputPrice string
@description('Output price per million tokens.')
param outputPrice string
@description('Cache-read price per million tokens.')
param cachedInputPrice string
@description('Price effective date.')
param priceDate string
@description('Authoritative price source.')
param priceSource string
@description('Verified billable input upper bound.')
param inputTokenLimit int
@description('Explicit verification of the deployment context-window bound.')
param contextBoundVerified bool
@description('Authoritative context-window specification.')
param contextBoundSource string
@description('Verified hard output-token limit.')
param outputTokenLimit int

resource environment 'Microsoft.App/managedEnvironments@2025-01-01' = {
  name: environmentName
  location: location
  tags: tags
  properties: {
    zoneRedundant: false
    appLogsConfiguration: {
      destination: 'none'
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

resource app 'Microsoft.App/containerApps@2025-01-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    environmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        allowInsecure: false
        targetPort: 8080
        transport: 'http'
      }
      secrets: [
        {
          name: 'run-signing-secret'
          value: signingSecret
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'broker'
          image: image
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'AZURE_CLIENT_ID', value: identityClientId }
            { name: 'BROKER_SIGNING_SECRET', secretRef: 'run-signing-secret' }
            { name: 'BROKER_BLOB_URL', value: storageAccountUrl }
            { name: 'BROKER_LEDGER_CONTAINER', value: ledgerContainer }
            { name: 'BROKER_MODEL_ENDPOINT', value: modelEndpoint }
            { name: 'BROKER_DEPLOYMENT', value: modelDeployment }
            { name: 'BROKER_API_VERSION', value: modelApiVersion }
            { name: 'BROKER_MODEL_VERSION', value: modelVersion }
            { name: 'BROKER_MODEL_NAME', value: modelName }
            { name: 'BROKER_INPUT_PRICE', value: inputPrice }
            { name: 'BROKER_OUTPUT_PRICE', value: outputPrice }
            { name: 'BROKER_CACHED_INPUT_PRICE', value: cachedInputPrice }
            { name: 'BROKER_PRICE_DATE', value: priceDate }
            { name: 'BROKER_PRICE_SOURCE', value: priceSource }
            { name: 'BROKER_INPUT_LIMIT', value: string(inputTokenLimit) }
            { name: 'BROKER_CONTEXT_BOUND_VERIFIED', value: toLower(string(contextBoundVerified)) }
            { name: 'BROKER_CONTEXT_BOUND_SOURCE', value: contextBoundSource }
            { name: 'BROKER_OUTPUT_LIMIT', value: string(outputTokenLimit) }
          ]
          probes: [
            {
              type: 'Startup'
              httpGet: { path: '/health', port: 8080, scheme: 'HTTP' }
              initialDelaySeconds: 1
              periodSeconds: 5
              failureThreshold: 10
              timeoutSeconds: 2
            }
            {
              type: 'Readiness'
              httpGet: { path: '/health', port: 8080, scheme: 'HTTP' }
              periodSeconds: 10
              failureThreshold: 3
              timeoutSeconds: 2
            }
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: 8080, scheme: 'HTTP' }
              periodSeconds: 20
              failureThreshold: 3
              timeoutSeconds: 2
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

output url string = 'https://${app.properties.configuration.ingress.fqdn}'
