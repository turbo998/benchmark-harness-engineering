targetScope = 'resourceGroup'

@description('Explicitly approved Azure region; no deployment is performed by this template.')
param location string

@description('Short lowercase alphanumeric naming prefix, validated by preflight.')
@minLength(2)
@maxLength(8)
param prefix string = 'bh'

@description('Frozen experiment ID used for ownership and cost tags.')
param runId string

@description('Owner of the experiment lifecycle and residual charges.')
param lifecycleOwner string

@description('Explicitly approved CPU VM SKU.')
param vmSize string

@description('Pinned Gen2 Linux image reference: publisher, offer, sku, version.')
param linuxImage object

@description('Non-root Linux administrator name.')
param adminUsername string = 'benchops'

@description('Operator SSH public key; SSH is not opened by the NSG.')
param sshPublicKey string

@description('Approved existing subnet with explicit egress, or empty to create a new private subnet.')
param existingSubnetId string = ''

@description('New VNet address space; check for overlap before apply.')
param vnetAddressPrefix string = '10.73.0.0/16'

@description('New worker subnet; check for overlap before apply.')
param subnetAddressPrefix string = '10.73.1.0/24'

@description('Optional explicit outbound NIC IP. Disabled by default; separately approve its charges.')
param enableOutboundPublicIp bool = false

@description('Immutable, accessible broker image reference including its sha256 digest.')
param brokerImage string

@description('Secure broker signing secret, never given to task containers.')
@secure()
@minLength(32)
param brokerSigningSecret string

@description('Approved Azure OpenAI HTTPS resource endpoint; no arbitrary target forwarding.')
param modelEndpoint string

@description('Existing approved inference deployment name.')
param modelDeployment string

@description('API version verified for the selected deployment protocol.')
param modelApiVersion string

@description('Frozen served model version used in accounting.')
param modelVersion string

@description('Frozen model family name returned by deployment control-plane metadata.')
param modelName string

@description('Authoritative input USD price per million tokens.')
param inputPricePerMillion string

@description('Authoritative output USD price per million tokens.')
param outputPricePerMillion string

@description('Authoritative cache-read USD price per million tokens.')
param cachedInputPricePerMillion string

@description('Price effective date and source are recorded by preflight.')
param priceDate string

@description('Authoritative source for the approved dated price table.')
param priceSource string

@description('Verified deployment context-window upper bound, not the desired prompt size.')
@minValue(1)
param modelInputTokenLimit int

@description('Approval confirms the full billable context-window bound was verified.')
@allowed([true])
param modelContextBoundVerified bool

@description('Authoritative context-window specification used for the input reservation.')
@minLength(1)
param modelContextBoundSource string

@description('Verified hard completion-token limit supported by the deployment.')
@minValue(1)
param modelOutputTokenLimit int

@description('Model account resource group, required only for approved role assignment.')
param modelResourceGroup string = ''

@description('Existing model account name, required only for approved role assignment.')
param modelAccountName string = ''

@description('Existing model account subscription; may differ from the experiment subscription.')
param modelSubscriptionId string = subscription().subscriptionId

@description('Create narrowly scoped inference role only when this role change was explicitly approved.')
param assignModelRole bool = false

var suffix = uniqueString(resourceGroup().id, runId)
var tags = {
  project: 'benchmark-harness-engineering'
  run_id: runId
  lifecycle_owner: lifecycleOwner
  data_classification: 'synthetic'
}

module identity './modules/identity.bicep' = {
  name: 'broker-identity'
  params: {
    name: 'id-${prefix}-${suffix}'
    location: location
    tags: tags
  }
}

module storage './modules/storage.bicep' = {
  name: 'evidence-storage'
  params: {
    name: 'st${prefix}${suffix}'
    location: location
    tags: tags
    brokerPrincipalId: identity.outputs.principalId
  }
}

module runner './modules/runner.bicep' = {
  name: 'isolated-runner'
  params: {
    name: 'vm-${prefix}-${suffix}'
    location: location
    tags: tags
    vmSize: vmSize
    imageReference: linuxImage
    adminUsername: adminUsername
    sshPublicKey: sshPublicKey
    existingSubnetId: existingSubnetId
    vnetAddressPrefix: vnetAddressPrefix
    subnetAddressPrefix: subnetAddressPrefix
    enableOutboundPublicIp: enableOutboundPublicIp
  }
}

module broker './modules/broker.bicep' = {
  name: 'trusted-inference-broker'
  params: {
    name: 'ca-${prefix}-${suffix}'
    environmentName: 'cae-${prefix}-${suffix}'
    location: location
    tags: tags
    identityId: identity.outputs.id
    identityClientId: identity.outputs.clientId
    image: brokerImage
    signingSecret: brokerSigningSecret
    storageAccountUrl: storage.outputs.accountUrl
    ledgerContainer: storage.outputs.ledgerContainer
    modelEndpoint: modelEndpoint
    modelDeployment: modelDeployment
    modelApiVersion: modelApiVersion
    modelVersion: modelVersion
    modelName: modelName
    inputPrice: inputPricePerMillion
    outputPrice: outputPricePerMillion
    cachedInputPrice: cachedInputPricePerMillion
    priceDate: priceDate
    priceSource: priceSource
    inputTokenLimit: modelInputTokenLimit
    contextBoundVerified: modelContextBoundVerified
    contextBoundSource: modelContextBoundSource
    outputTokenLimit: modelOutputTokenLimit
  }
}

module inferenceRole './modules/inference-role.bicep' = if (assignModelRole) {
  name: 'approved-inference-role'
  scope: resourceGroup(modelSubscriptionId, modelResourceGroup)
  params: {
    accountName: modelAccountName
    principalId: identity.outputs.principalId
  }
}

output runnerId string = runner.outputs.id
output runnerName string = runner.outputs.name
output brokerUrl string = broker.outputs.url
output brokerIdentityId string = identity.outputs.id
output storageAccountName string = storage.outputs.name
output artifactContainer string = storage.outputs.artifactContainer
output ledgerContainer string = storage.outputs.ledgerContainer
output runId string = runId
