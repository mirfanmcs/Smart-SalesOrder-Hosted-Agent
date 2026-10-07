# Smart Sales Order Hosted Agent

This project implements `order-management-agent`, a standalone
Python-hosted Microsoft Foundry agent for product catalog operations, store
knowledge, sales-order analytics, and restricted public-web product research.

The repository follows the same container build, Python SDK deployment, folder
structure, and GitHub Actions pattern as
`Simple-Agent-App-Hosted-Agent`.

This project demonstrates the use of:
- An existing REST API exposed through an MCP endpoint hosted on API Management
- Three IQ capabilities of Microsoft IQ:
  - Foundry IQ
  - Fabric IQ
  - Web IQ

## Architecture

```text
Browser
  |
  v
client-app container (Flask)
  |
  v
order-management-agent-python (Foundry hosted Responses agent)
  |-- Product API MCP
  |-- order-mgt-kb knowledge base
  |-- SalesOrderDataagent through Fabric IQ
  `-- Order-Mgt-WebIQ (web and browse only for product research)
```

`Agents/hosted_agent_definition.py` contains the complete agent instructions
and all four server-side Foundry tool definitions. It does not call another
agent. Each tool uses a dedicated Foundry project connection created for this
Python agent, allowing the platform to apply the required authentication
without storing secrets in the container.

The agent supports:

- Internal product catalog reads and explicit create, update, and delete
  operations through Product API MCP.
- Store policy, privacy, security, payment, shipping, return, refund, terms,
  and conditions grounding through `order-mgt-kb`.
- Sales order, customer, quantity, revenue, status, performance, and trend
  analysis through `SalesOrderDataagent` and Fabric IQ.
- Public-web product research through Web IQ, restricted to the `web` and
  `browse` tools.
- Strict refusal, grounding, citation, data-protection, and anti-fabrication
  rules implemented directly in the Python instructions.

## Project structure

```text
Smart-SalesOrder-Hosted-Agent/
|-- .github/
|   `-- workflows/
|       `-- deploy-simple-hosted-agent.yaml
|-- Agents/
|   |-- .dockerignore
|   |-- .env.example
|   |-- Dockerfile
|   |-- deploy_hosted_agent.py
|   |-- hosted_agent_definition.py
|   `-- pyproject.toml
|-- client-app/
|   |-- static/
|   |   |-- app.js
|   |   `-- styles.css
|   |-- templates/
|   |   `-- index.html
|   |-- .dockerignore
|   |-- .env.example
|   |-- Dockerfile
|   |-- app.py
|   `-- requirements.txt
|-- .gitignore
|-- install.sh
|-- requirements.txt
`-- README.md
```

## Prerequisites

- Python 3.13.
- Azure CLI authenticated with `az login`.
- Docker Desktop for local container builds, or an Azure Container Registry
  for remote builds.
- Access to the existing Foundry project:
  `https://order-mgt-resource.services.ai.azure.com/api/projects/order-mgt-project`.
- The `gpt-5.4` model deployment.
- `Foundry Project Manager` to create hosted agent versions.
- ACR push permission for the deployment identity.
- `Container Registry Repository Reader` or `AcrPull` for the Foundry project's
  managed identity.
- The dedicated project connections named in `Agents/.env.example`.
- A Product API access key stored in the `product-api-python-agent` Foundry
  connection.
- A dedicated Fabric service principal with Contributor access to the Fabric
  workspace and read access to every data source used by the data agent.
- The Fabric tenant setting **Service principals can use Fabric APIs**
  enabled for that service principal or a security group containing it.

## Agent configuration

Create the agent's private environment file:

```powershell
Copy-Item Agents\.env.example Agents\.env
```

Configure `Agents\.env`:

```env
PROJECT_ENDPOINT=https://order-mgt-resource.services.ai.azure.com/api/projects/order-mgt-project
DEPLOYMENT_NAME=gpt-5.4
HOSTED_AGENT_NAME=order-management-agent-python
HOSTED_AGENT_IMAGE=<acr-name>.azurecr.io/order-management-agent:<tag>
PRODUCT_API_MCP_URL=https://irf-api-mgt.azure-api.net/product-api-mcp/mcp
PRODUCT_API_CONNECTION_ID=product-api-python-agent
FNDY_IQ_MCP_URL=https://order-mgt-ai-search.search.windows.net/knowledgebases/order-mgt-kb/mcp?api-version=2026-08-01-preview
FNDY_IQ_CONNECTION_ID=order-kb-python-agent
FABRIC_IQ_URL=https://<fabric-host>/v1/mcp/workspaces/<workspace-id>/dataagents/<data-agent-id>/agent
FABRIC_IQ_CREDENTIAL_CONNECTION_ID=sales-iq-python-agent-credentials
WEB_IQ_MCP_URL=https://api.microsoft.ai/v3/mcp
WEB_IQ_CONNECTION_ID=web-iq-python-agent
WEB_IQ_API_KEY=<web-iq-access-key>
```

Both `Agents\hosted_agent_definition.py` and
`Agents\deploy_hosted_agent.py` explicitly load `Agents\.env`, regardless of
the current working directory.

Do not commit `Agents\.env`. `WEB_IQ_API_KEY` is used only when creating or
updating the `web-iq-python-agent` Foundry connection. The hosted agent uses
the connection ID, so the raw key is not passed to the model, included in the
container image, or injected into the hosted-agent runtime environment.

### Independent Foundry connections

This agent uses four dedicated project connections:

| Connection | Authentication | Purpose |
|---|---|---|
| `product-api-python-agent` | `CustomKeys` | Product API MCP |
| `order-kb-python-agent` | `ProjectManagedIdentity` | Knowledge-base MCP |
| `sales-iq-python-agent-credentials` | `CustomKeys` | Secure Fabric service-principal credentials |
| `web-iq-python-agent` | `CustomKeys` | Web IQ MCP |

Fabric IQ is called directly with the hosted agent's dedicated service
principal because Fabric data agents do not support managed identity
authentication. Its tenant ID, client ID, and secret are stored in the
`sales-iq-python-agent-credentials` Foundry connection and retrieved only by
the hosted runtime. Grant the service principal Fabric workspace Contributor
access and read access to every data source attached to the data agent. Add
the service principal to the `research-iq-fabric-identities` Entra security
group, which is scoped by the Fabric tenant setting **Service principals can
use Fabric APIs**.

The Web IQ connection stores the `x-apikey` credential securely in Foundry.
Keep the source value only in the ignored `Agents\.env` file or the GitHub
`AGENT_ENV` repository secret. Never place the key in Python code, workflow
YAML, Docker files, command output, or committed documentation.

## Client app configuration

Create a separate environment file for the UI:

```powershell
Copy-Item client-app\.env.example client-app\.env
```

Configure `client-app\.env`:

```env
PROJECT_ENDPOINT=https://order-mgt-resource.services.ai.azure.com/api/projects/order-mgt-project
HOSTED_AGENT_NAME=order-management-agent-python
CLIENT_PORT=8080
```

`client-app\app.py` explicitly loads `client-app\.env`, regardless of the
current working directory. Do not commit this file. The client starts without
`PROJECT_ENDPOINT`; chat requests then return a clear agent-unavailable
response until the endpoint is configured.

The repository root does not use a `.env` file. Agent and client settings are
kept separate and neither application searches the working directory for
configuration.

`order-mgt-kb` remains unchanged and is currently the target of
`order-kb-python-agent`. When the new knowledge base is available, update the
`order-kb-python-agent` connection target and set `FNDY_IQ_MCP_URL` to its
MCP URL. The connection ID remains stable, so the Python source does not need
to change.

## Sample prompts

The following prompts exercise every configured tool and routing path.

### Product API MCP

| Tool | Sample prompt |
|---|---|
| `listProducts` | `List all products currently available in the internal catalog.` |
| `getProductById` | `Get the complete product details for product ID 42.` |
| `getProductByCode` | `Find the product with code LAPTOP-001 and show its catalog details.` |
| `createProduct` | `Create a product named Contoso Travel Mouse with code MOUSE-TRAVEL-01 and price 39.95.` |
| `updateProduct` | `Update product code MOUSE-TRAVEL-01 so its price is 34.95.` |
| `deleteProduct` | `Delete the product with code MOUSE-TRAVEL-01.` |

Use create, update, and delete prompts only against a development or test
catalog unless the change is intentionally required in production.

### Store knowledge base

These prompts route to `knowledge_base_retrieve` on `order-mgt-kb`:

- `What is the return and refund policy?`
- `What payment methods does the store accept?`
- `Summarize the shipping policy and expected delivery times.`
- `What privacy and security protections apply to customer information?`
- `What are the store terms and conditions for cancelled orders?`

### Fabric IQ sales-order analysis

These prompts route to `SalesOrderDataagent`:

- `Summarize overall sales order performance.`
- `Show monthly revenue and order count for the last 12 months.`
- `Which customers generated the highest sales revenue?`
- `Show order quantities and sales amounts grouped by product.`
- `List open or delayed orders and include the customer and order status.`
- `Compare sales trends for the current quarter with the previous quarter.`
- `For customer Contoso Ltd, summarize orders, quantities, and revenue between January 1, 2026 and September 26, 2026.`

### Web IQ product research

These prompts use only the Web IQ `web` and `browse` tools:

- `Research three current noise-cancelling headphones under $300 and compare price, features, battery life, and warranty. Cite the sources.`
- `Compare Microsoft Surface Laptop and Dell XPS 13 specifications and public pricing from the manufacturers' websites.`
- `Find current alternatives to the Sony WH-1000XM5, then compare their published features and prices.`
- `Browse this product page and summarize the specifications, warranty, and listed price: https://www.microsoft.com/surface.`
- `Research public reviews for three business laptops and clearly distinguish manufacturer claims from independent review findings.`

Web IQ must not be used for unrelated searches. For example, prompts such as
`Search the web for today's Microsoft stock price` or
`Find today's sports scores` should return the configured out-of-scope
response without calling a web tool.

### Cross-source routing checks

- `Is product code LAPTOP-001 in the catalog, and what is the store return policy for it?`
- `Compare catalog product LAPTOP-001 with similar public-web products, but do not expose customer or order data to Web IQ.`
- `Show sales performance for product LAPTOP-001 and keep the catalog record separate from transactional sales results.`
- `What is the refund policy for an order that has already shipped? Use policy knowledge only; do not search the public web.`

## Run the hosted agent locally

Create the environment and install the hosted runtime:

```powershell
Set-Location Agents
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --editable .
```

Copy and configure `Agents\.env` as described above, then start the Responses
server:

```powershell
.\.venv\Scripts\python.exe hosted_agent_definition.py
```

The local Responses endpoint listens on port `8088`.

The local credential chain uses `DefaultAzureCredential`. For developer use,
authenticate with `az login`. Do not place Azure access tokens in
`Agents\.env`.

Product API, knowledge retrieval, Fabric IQ, and Web IQ can be tested locally
when the developer identity can use the configured Foundry connections.
Fabric also requires its service principal to be allowed by the tenant-level
Fabric API setting.

## Build the hosted agent image

Build locally:

```powershell
docker build -t order-management-agent:local Agents
```

Run locally:

```powershell
docker run --rm -p 8088:8088 `
  --env-file Agents\.env `
  order-management-agent:local
```

For local Docker authentication, provide a supported workload identity or
developer credential to the container. Do not copy Azure CLI token caches into
production images.

Build and push with ACR:

```powershell
$tag = (git rev-parse --short HEAD)
az acr build `
  --registry "<acr-name>" `
  --image "order-management-agent:$tag" `
  --platform linux/amd64 `
  Agents
```

Set `HOSTED_AGENT_IMAGE` to the resulting immutable image URI.

## Deploy the agent to Microsoft Foundry

Install deployment dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --requirement requirements.txt
```

Deploy:

```powershell
.\.venv\Scripts\python.exe Agents\deploy_hosted_agent.py
```

Or pass values explicitly:

```powershell
.\.venv\Scripts\python.exe Agents\deploy_hosted_agent.py `
  --project-endpoint "https://order-mgt-resource.services.ai.azure.com/api/projects/order-mgt-project" `
  --model-deployment "gpt-5.4" `
  --image "<acr-name>.azurecr.io/order-management-agent:<tag>"
```

The script:

1. Creates a hosted-agent version named `order-management-agent-python`.
2. Injects the model, MCP endpoint, and Foundry connection settings.
3. Configures the Responses protocol.
4. Waits for the version to become active.
5. Routes 100% of endpoint traffic to the new version.

## GitHub Actions deployment

`.github/workflows/deploy-order-management-agent.yaml` uses a two-job
build/deploy pattern:

1. `Build` uses `az acr build` and tags the agent image with
   `${{ github.sha }}`.
2. `Deploy` installs the Python SDK dependencies and runs
   `Agents/deploy_hosted_agent.py`.

Required repository secret:

- `AZURE_CREDENTIALS_AGENT_DEPLOY`: JSON credentials for `azure/login`.
  Its service principal requires `Container Registry Tasks Contributor` on
  the target ACR and `Foundry User` on the target Foundry project.
- `ENV`: complete `Agents\.env` content. It must include
  `PROJECT_ENDPOINT`, `DEPLOYMENT_NAME`, `HOSTED_AGENT_NAME`,
  `HOSTED_AGENT_IMAGE`, and the tool connection settings from
  `Agents\.env.example`.

Required repository variable:

- `ACR_NAME`: Azure Container Registry resource name.

The workflow is manually triggered. Uncomment the `push` block to enable
path-filtered automatic deployments.

## Run the client UI locally

Create and activate a separate environment:

```powershell
Set-Location client-app
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --requirement requirements.txt
```

Copy and configure the client environment file, then start the app:

```powershell
Copy-Item .env.example .env
.\.venv\Scripts\python.exe app.py
```

Open `http://localhost:8080`.

The client maintains the Foundry `previous_response_id` in browser memory.
Use **New conversation** to reset the conversation. The UI process does not
require the hosted agent to be available at startup.

## Build the client container

```powershell
docker build -t order-management-client:local client-app
docker run --rm -p 8080:8080 `
  --env-file client-app\.env `
  order-management-client:local
```

If the build environment requires a Python package mirror, pass it without
changing the image definition:

```powershell
docker build `
  --build-arg PIP_INDEX_URL="https://your-package-index/simple/" `
  -t order-management-client:local `
  client-app
```

The health endpoint is `GET /health`.

## Deploy the client to Azure Container Apps

Create or choose a resource group, Container Apps environment, and ACR:

```powershell
$resourceGroup = "<resource-group>"
$location = "westus3"
$environment = "<container-app-environment>"
$acrName = "<acr-name>"
$clientApp = "order-management-client"
$tag = (git rev-parse --short HEAD)

az group create --name $resourceGroup --location $location
az containerapp env create `
  --name $environment `
  --resource-group $resourceGroup `
  --location $location

az acr build `
  --registry $acrName `
  --image "order-management-client:$tag" `
  --platform linux/amd64 `
  client-app
```

Create the Container App with a system-assigned managed identity:

```powershell
$loginServer = az acr show `
  --name $acrName `
  --query loginServer `
  --output tsv

az containerapp create `
  --name $clientApp `
  --resource-group $resourceGroup `
  --environment $environment `
  --image "$loginServer/order-management-client:$tag" `
  --target-port 8080 `
  --ingress external `
  --system-assigned `
  --registry-server $loginServer `
  --env-vars `
    PROJECT_ENDPOINT="https://order-mgt-resource.services.ai.azure.com/api/projects/order-mgt-project" `
    HOSTED_AGENT_NAME="order-management-agent-python"
```

Grant the Container App managed identity access to the Foundry project:

```powershell
$principalId = az containerapp identity show `
  --name $clientApp `
  --resource-group $resourceGroup `
  --query principalId `
  --output tsv

$projectId = "/subscriptions/<subscription-id>/resourceGroups/irf-order-management/providers/Microsoft.CognitiveServices/accounts/order-mgt-resource/projects/order-mgt-project"

az role assignment create `
  --assignee-object-id $principalId `
  --assignee-principal-type ServicePrincipal `
  --role "Foundry User" `
  --scope $projectId
```

Use the least-privileged project-level role that can invoke the agent.

When the ACR does not allow admin credentials, grant the Container App identity
`AcrPull` and configure the registry identity:

```powershell
$acrId = az acr show --name $acrName --query id --output tsv

az role assignment create `
  --assignee-object-id $principalId `
  --assignee-principal-type ServicePrincipal `
  --role AcrPull `
  --scope $acrId

az containerapp registry set `
  --name $clientApp `
  --resource-group $resourceGroup `
  --server $loginServer `
  --identity system
```

Show the public URL:

```powershell
az containerapp show `
  --name $clientApp `
  --resource-group $resourceGroup `
  --query properties.configuration.ingress.fqdn `
  --output tsv
```

## Security and operational notes

- No MCP keys, connection secrets, Azure tokens, customer data, or order data
  are stored in this repository.
- Product, knowledge, Fabric IQ, and Web IQ routing rules are defined directly
  in `Agents/hosted_agent_definition.py`.
- Web IQ is restricted in code to `web` and `browse`, and the instructions
  limit both tools to public-web product research.
- The client app uses managed identity in Azure and `DefaultAzureCredential`
  locally.
- Use immutable image tags for both containers.
- Keep `WEB_IQ_API_KEY` only in the ignored `Agents\.env` file or the GitHub
  `AGENT_ENV` secret. Use it to provision the Foundry connection, not as an
  agent runtime variable.
- Keep the Product API key and Fabric service-principal secret only in their
  Foundry connections. The hosted runtime retrieves the Fabric credential at
  startup; neither secret is embedded in source code or the container image.
- Restrict client ingress or add application authentication before exposing
  production business data.
- Fabric IQ uses the dedicated service principal stored in
  `sales-iq-python-agent-credentials`. Ensure the Fabric tenant permits that
  principal to call Fabric public APIs.
