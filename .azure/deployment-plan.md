# Azure deployment status

**Template design approved; not deployed.** Actual environment binding, live
preflight, what-if, role changes, apply and paid smoke are not approved or executed.

The parameterized architecture is described in `infrastructure-plan.json`:
one Linux Docker-capable VM with no managed identity, an independent trusted
Container Apps inference broker, its own least-privilege identity, and private
Blob evidence/ledger containers. Existing approved inference deployments are
preferred; this template does not create a model deployment.

Required binding before cloud validation:

- Subscription, resource group, region, CPU SKU/image and approved resource count.
- Explicit existing egress or the separately approved outbound-IP option.
- Model endpoint/deployment/version/API protocol, context/output limits and
  authoritative dated input/output/cache prices.
- Operator permissions, regional/family quota, SKU restrictions, registrations,
  model RPM/TPM and actual inference role.
- Secure broker image and secret delivery, run budget, expiry and lifecycle owner.
- Independent verified evidence export destination and compute-stop/watchdog.

Local compilation/offline tests do not establish live deployability. After
binding, run read-only preflight and what-if, then `azure-validate`; only separately
approved `azure-deploy` may apply the selected resource set. Destructive cleanup
requires explicit authorization and a verified complete export receipt.
