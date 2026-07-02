# NAVIXA AI — Multi-Cloud Hub-and-Spoke Network Architecture Audit Platform
## Development Prompt (Master)

---

## 1. Product Branding & Platform Identity

### Product Name
**NAVIXA AI** — Network Architecture Visibility & Exposure Analytics

### Product Description
NAVIXA AI is an AI-powered multi-cloud network architecture intelligence platform that automatically discovers cloud networking components, validates Hub-and-Spoke architectures, analyzes internet exposure paths, visualizes network topologies, and generates actionable audit and security insights across **AWS, Azure, GCP, and OCI**.

### Tagline
*"Transforming Cloud Network Complexity Into Actionable Intelligence."*

### Mission
Provide organizations with complete visibility into multi-cloud network architectures by combining automated discovery, graph-based topology analysis, AI-powered correlation, architectural compliance validation, and exposure analytics within a single platform.

### Branding Requirements by Surface

| Surface | Content |
|---|---|
| **Login Screen** | NAVIXA AI — AI-Powered Multi-Cloud Network Architecture Visibility & Exposure Analytics — "Transforming Cloud Network Complexity Into Actionable Intelligence" |
| **Dashboard Header** | NAVIXA AI — Multi-Cloud Network Architecture Intelligence Platform |
| **Documentation Header** | NAVIXA AI — AI-Powered Multi-Cloud Network Architecture Visibility & Exposure Analytics |
| **Repository Name** | `navixa-ai` |
| **Database Names** | `navixa_db` (PostgreSQL) · `navixa_graph` (Neo4j) · `navixa_cache` (Redis) |

---

## 2. NAVIXA AI Platform Modules

These module names should be used consistently across UI, API route naming/tags, backend service/package naming, and documentation.

### NAVIXA Discover
- Multi-cloud inventory collection
- Network discovery
- Asset enumeration
- Tenant onboarding
- Configuration collection
- AWS, Azure, GCP, OCI support

### NAVIXA Topology
- Topology generation
- Network relationship mapping
- Interactive network diagrams
- Graph visualization
- Hub-and-Spoke diagrams
- Connectivity graphs

### NAVIXA Pathfinder
- Internet exposure analysis
- Ingress path analysis
- Egress path analysis
- Route tracing
- Reachability validation

### NAVIXA Validate
- Hub-and-Spoke validation
- Architecture compliance checks
- Route validation
- Segmentation validation
- Unauthorized peering detection
- Hub bypass detection

### NAVIXA Graph
- Network relationship modeling
- Graph creation
- Dependency analysis
- NetworkX
- Neo4j

### NAVIXA InsightAI
- AI-powered network correlation
- Audit observation generation
- Root cause analysis
- Remediation recommendation generation
- Executive summary generation
- Architecture explanation

**Supported AI Providers:**
- Claude API
- OpenAI GPT
- Azure OpenAI
- Gemini
- AWS Bedrock

### NAVIXA Reports
- Executive reports
- Technical reports
- Compliance reports
- PDF, Excel, and HTML export

### NAVIXA Watch *(Future)*
- Continuous monitoring
- Change detection
- Drift analysis
- Alert generation

---

## 3. User Workflow

```
Login
  → Select Cloud Provider
  → Select Tenant
  → Authenticate Using Cloud SSO
  → Select Account / Subscription / Project
  → Select Hub Network
  → Run NAVIXA Discover
  → Generate NAVIXA Topology
  → Run NAVIXA Validate
  → Run NAVIXA Pathfinder
  → Generate NAVIXA InsightAI Analysis
  → Export NAVIXA Reports
```

---

## 4. Objective

Develop an enterprise-grade web application — **NAVIXA AI** — to perform multi-cloud network architecture audits across **AWS, Azure, GCP, and OCI**, with a primary focus on:
- Hub-and-Spoke validation (NAVIXA Validate)
- Internet exposure analysis (NAVIXA Pathfinder)
- Topology visualization (NAVIXA Topology)
- AI-assisted audit findings (NAVIXA InsightAI)

---

## 5. Technology Stack

**Backend:** Python 3.x, FastAPI, SQLAlchemy, Pydantic, Alembic, Celery, Redis
**Database:** PostgreSQL (`navixa_db` — application data), Neo4j (`navixa_graph` — graph relationships), Redis (`navixa_cache`)
**Frontend MVP:** Streamlit or NiceGUI
**Enterprise Frontend:** React, TypeScript, Material UI, React Flow, Cytoscape.js

---

## 6. Authentication

- **Development:** Local authentication with JWT, password hashing, RBAC
- **Production:** Microsoft Entra ID, OAuth2, OIDC, MFA
- **Roles:** Admin, Auditor, Viewer

### Login Screen — Dual Authentication Path

The NAVIXA AI login screen presents **two options**:

- **Local Admin Login** — username/password against the local PostgreSQL-backed user store, JWT issued on success. This is the fallback/dev-convenience path and always available for the seeded Admin account, regardless of environment.
- **Sign in with SSO** — Microsoft Entra ID (OAuth2/OIDC, MFA-capable). Selecting this redirects to Entra ID's interactive login; on successful auth, NAVIXA maps the returned identity to a NAVIXA RBAC role (Admin/Auditor/Viewer) via the Users/Roles tables.

Both paths issue the same internal JWT/session format to the rest of the application — downstream services (API, RBAC checks) don't need to know which login path was used.

> Note: this Entra ID SSO at the login screen is for **NAVIXA application access** (who can log into NAVIXA and what they can see). It is separate from the **per-cloud-provider authentication** (AWS/Azure/GCP/OCI credentials used by NAVIXA Discover to call cloud APIs), covered in Section 8a — a user can log into NAVIXA via Local Admin and still have NAVIXA Discover use their delegated cloud credentials, and vice versa.

Whether a developer logs into NAVIXA itself via Local Admin or Entra SSO, their identity is provisioned as a normal row in the Users/Roles tables mapped to the **NAVIXA Admin** role during the dev phase — not a hardcoded bypass — so the same RBAC model scales to real multi-user setups later.

---

## 7. Security Requirements

- No secrets stored in source code
- Use environment variables during development
- Use Secret Managers / Key Vaults in production
- Frontend must never access secrets
- All cloud and AI API calls must occur through backend services only

---

## 8. Cloud Authentication

- **AWS:** IAM Identity Center, AssumeRole
- **Azure:** Entra ID OAuth
- **GCP:** Workforce Identity Federation
- **OCI:** Federation and Identity Domains
- Use **temporary credentials only** — no long-lived keys

---

## 8a. Dev-Time Cloud Provider Authentication, Caching & Future App Registration

### Dev-Time Cloud Provider Authentication (Delegated / Interactive User Auth)

During development, NAVIXA AI authenticates to each **cloud provider** as the developer, using delegated/interactive sign-in rather than a standing service identity:

- **Azure:** Entra ID interactive login (OAuth2 Authorization Code flow via MSAL) — the developer's own Entra ID account.
- **AWS:** IAM Identity Center SSO login using the developer's own permission set/assignment.
- **GCP:** User credentials via interactive OAuth (equivalent of `gcloud auth application-default login`), scoped to the developer's own IAM role bindings.
- **OCI:** Browser-based SSO / Identity Domains login using the developer's own user identity.
- All calls to cloud provider APIs run under the permissions already granted to the developer's own account (assumed Admin-equivalent for this dev phase) — no separate service credentials yet.
- Still complies with Section 8: **temporary, short-lived tokens only** — only *whose* identity issues the token differs in this phase, not the credential lifetime rule.

### Temporary Result Caching (Avoid Redundant Cross-Cloud API Calls)

- Store normalized discovery + analysis results in `navixa_cache` (Redis) with a configurable TTL (default 30–60 minutes).
- Cache key scoped per tenant + account/subscription/project + resource type, so partial cache hits are possible.
- Every audit run exposes a **"Force Refresh"** option that bypasses cache and re-queries live cloud APIs.
- Cached data flagged clearly in UI/API response (`"source": "cache"` vs `"live"`, with `cached_at` timestamp).
- Sits between NAVIXA Discover and NAVIXA Graph/Validate — doesn't change the normalized data model, only call frequency.

### Future State: Azure Entra ID App Registration (Seamless / Headless Cloud Auth)

- Support two **cloud-provider** auth modes per tenant from day one at the interface level:
  - **Delegated mode** (current): interactive user sign-in, token acquired on behalf of a signed-in human.
  - **App-only mode** (future): Entra ID App Registration using client credentials flow (service principal + client secret/certificate, stored in Key Vault) — no human sign-in required, enabling scheduled/automated audit runs.
- Tenant Registry (Section 9) stores which auth mode a tenant uses, plus non-sensitive app registration metadata (Client ID, Tenant ID, redirect URI) — secrets stay in Key Vault only.
- NAVIXA Discover's cloud API calls are written against an AuthProvider interface, not a specific flow — collectors work unchanged regardless of active mode per tenant.

### Test App Registration (Validate the Future Path Now)

- An existing **test Entra ID app registration** (limited resources) is used now, in parallel with delegated dev auth, to validate the app-only/client-credentials path end-to-end.
- Wired into the Tenant Registry as a second, clearly-labeled test tenant (e.g., `tenant_name: "NAVIXA Test — App Registration"`), separate from the primary admin-delegated tenant, so both auth paths can be exercised side by side during development.

---

## 9. Tenant Registry

Store non-sensitive metadata only:
- Cloud Provider
- Tenant Name
- Tenant ID
- Organization ID
- SSO/Login URL
- Region Information
- Cloud Auth Mode (`delegated` | `app_only` — see Section 8a)
- App Registration metadata when in `app_only` mode: Client ID, Tenant ID, Redirect URI (non-sensitive only; secrets live in Key Vault, never here)

---

## 10. Cloud Discovery Modules (NAVIXA Discover)

### AWS
Organizations, Accounts, VPCs, Subnets, Route Tables, IGW, NAT, TGW, Security Groups, NACLs, VPC Endpoints, Network Interfaces, EC2, ALB/NLB, Direct Connect, VPN

### Azure
Tenants, Subscriptions, VNets, Subnets, NSGs, Route Tables, UDRs, Public IPs, NICs, Peerings, Azure Firewall, Load Balancers, Application Gateway, ExpressRoute, Virtual WAN, Private Endpoints, VMs

### GCP
Organizations, Projects, VPCs, Subnets, Firewall Rules, Routes, Cloud Router, Cloud NAT, VPN, Interconnect, Load Balancers, VMs, External IPs, Peerings

### OCI
Tenancies, Compartments, VCNs, Subnets, Route Tables, DRGs, LPGs, Internet/NAT Gateways, Security Lists, NSGs, Compute Instances, Load Balancers

---

## 10a. Concurrent Multi-Cloud Resource Discovery (NAVIXA Discover — Concurrency Design)

### Objective
NAVIXA Discover must fetch multiple resource types (VPCs, Subnets, Route Tables, Security Groups, Gateways, Load Balancers, etc.) from a cloud provider **in parallel**, not sequentially, to reduce total audit time — and must do this **per account/subscription/project and across multiple tenants simultaneously** where the user has selected multiple scopes.

### Design Requirements

**1. Concurrency Model**
- Use `asyncio` + `httpx.AsyncClient` (or provider SDK async clients where available: `aioboto3` for AWS, `azure-*-aio` for Azure, native async for GCP/OCI where supported) so I/O-bound cloud API calls don't block each other.
- Each resource-type collector (VPCs, Subnets, Security Groups, Route Tables, etc.) runs as an independent async task; results are gathered with `asyncio.gather()` per account/subscription/project.
- Celery remains the outer job orchestrator (one Celery task per tenant/account audit run); inside that task, the async event loop drives the fan-out of resource calls.

**2. Concurrency Limits & Throttling**
- Respect each cloud provider's API rate limits — implement a configurable **semaphore/connection pool per provider** (e.g., max N concurrent calls to AWS EC2 API, separate limit for AWS ELB API, etc.) to avoid throttling (`Throttling`, `TooManyRequestsException`, `429`).
- Rate limit configuration should live in `config/` per provider, not hardcoded.
- Implement exponential backoff + jitter retry logic for throttled/failed calls.

**3. Multi-Scope Parallelism**
- When a user selects multiple accounts/subscriptions/projects/tenancies, NAVIXA Discover should fan out discovery jobs across them concurrently (bounded by a configurable max-parallel-scopes setting), not one at a time.
- Each scope's discovery result is independent and fault-isolated — one account's failure/timeout must not block or fail other accounts' discovery.

**4. Partial Failure Handling**
- If one resource-type call fails (e.g., Security Groups fetch fails but VPCs succeeds), the collector should record a partial-failure status for that resource type, continue collecting everything else, and surface it as a discovery warning — not fail the entire audit job.
- Store per-resource-type collection status (success / partial / failed) with error details for observability.

**5. Progress Tracking**
- Since multiple resource types and multiple scopes run concurrently, provide real-time job progress (e.g., via WebSocket or polling endpoint) showing per-scope, per-resource-type completion status — useful for large enterprise environments with hundreds of accounts.

**6. Normalization After Fan-In**
- All parallel results converge into the common Data Normalization model (Section 11 below) after collection completes, before being written to PostgreSQL/Neo4j — ensuring downstream Graph/Validate/Pathfinder stages always see a consistent, fully-normalized dataset regardless of collection order.

**7. Performance Targets (guidance for Claude Code to design against)**
- Should be architected so discovery time scales with the *slowest* resource-type/API call per scope, not the *sum* of all calls.
- Should support horizontal scaling of Celery workers to increase parallel scope throughput as tenant/account count grows.

---

## 11. Data Normalization

Create a common network model shared across all cloud providers:
- Network
- Subnet
- Route Table
- Route
- Gateway
- Firewall
- Security Group
- Network Interface
- Load Balancer
- Endpoint
- Compute Instance
- Peering Connection
- Public IP

---

## 12. Graph Engine (NAVIXA Graph)

Use **NetworkX** and **Neo4j** (`navixa_graph`).

Capabilities:
- Path traversal
- Reachability analysis
- Route analysis
- Dependency mapping
- Internet exposure tracing

---

## 13. Hub-and-Spoke Validation (NAVIXA Validate)

- User selects approved Hub VPCs/VNets
- Detect unauthorized peering
- Detect spoke-to-spoke communication
- Detect internet exposure
- Detect routing bypass
- Detect segmentation violations

---

## 14. Internet Path Analysis (NAVIXA Pathfinder)

Evaluate:
- Public IPs
- Route tables
- Gateways
- Security Groups
- Firewalls
- Load Balancers

Generate ingress and egress path analysis.

---

## 15. AI Layer (NAVIXA InsightAI)

Create a provider abstraction layer:
- Claude Provider
- OpenAI Provider
- Azure OpenAI Provider
- Gemini Provider
- AWS Bedrock Provider
- Future providers (extensible interface)

### AI Use Cases
- Findings generation
- Connectivity explanation
- Recommendation generation
- Executive summaries
- Topology explanation
- Root cause analysis

---

## 16. Visualization (NAVIXA Topology)

Support:
- Hub-and-Spoke diagrams
- Route visualization
- Internet path visualization
- Peering relationships
- Transit Gateway and Virtual WAN visualization

---

## 17. Reporting (NAVIXA Reports)

Generate reports in:
- HTML
- PDF
- Excel

Including findings, evidence, topology, severity, recommendations, and executive summaries. Report types: Executive, Technical, Compliance.

---

## 18. Background Processing

Use **Celery** and **Redis** (`navixa_cache`).

Workflow:
```
User -> Audit Job -> Queue -> NAVIXA Discover -> NAVIXA Graph -> NAVIXA Validate -> NAVIXA Pathfinder -> NAVIXA InsightAI -> NAVIXA Reports
```

---

## 19. Recommended Project Structure

```
navixa-ai/
├── frontend/
├── backend/
├── api/
├── auth/
├── collectors/              # NAVIXA Discover
├── graph_engine/            # NAVIXA Graph
├── internet_path_engine/    # NAVIXA Pathfinder
├── hub_spoke_validator/     # NAVIXA Validate
├── ai_engine/                # NAVIXA InsightAI
├── reports/                  # NAVIXA Reports
├── workers/
├── tenant_registry/
├── visualization/            # NAVIXA Topology
├── database/
├── config/
├── tests/
├── docker/
├── docs/
├── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## 19a. Version Control & Repo Setup

The `navixa-ai` repository is already initialized locally and connected to a remote (GitHub) before Claude Code begins scaffolding. Claude Code should commit incrementally into this existing repo — not treat repo initialization as its own task — and follow these conventions:

### Branch Strategy
- `main` — always deployable; protected, no direct commits once collaborators are added
- `develop` — integration branch for in-progress phase work (optional but recommended once past solo scaffolding)
- `feature/<phase>-<short-desc>` — one branch per meaningful unit of work, e.g.:
  - `feature/phase1-fastapi-skeleton`
  - `feature/phase1-jwt-auth`
  - `feature/phase1-aws-collector`
  - `feature/phase1-hub-spoke-validation`
- `fix/<short-desc>` for bug fixes
- `chore/<short-desc>` for tooling/config/non-feature changes

### Commit Message Convention (Conventional Commits)
Format: `<type>(<scope>): <short description>`

| Type | Use for |
|---|---|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `chore` | Tooling, config, dependency bumps |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |

Examples:
- `feat(auth): add JWT-based local authentication`
- `feat(collectors): add async AWS VPC and subnet collector`
- `docs(architecture): add Phase 1 component diagram`
- `chore(docker): add docker-compose for postgres, redis, neo4j`

### Commit Granularity
- One logical unit of work per commit (e.g., "add SQLAlchemy tenant model" is its own commit, not bundled with "add auth routes").
- Avoid single giant commits that dump an entire phase's scaffolding at once — this breaks reviewability and rollback.
- Generated code from each step in Section 22 (architecture doc, DB schema, API skeleton, backlog, sprint plan, starter code, env setup) should land as separate, clearly labeled commits.

### What Claude Code Should NOT Do
- Do not run `git init` (already done) or create/rename the remote.
- Do not force-push to `main`.
- Do not commit `.env` files, credentials, or any secrets — `.gitignore` already excludes these; Claude Code must not override or bypass it.

---

## 20. Development Roadmap

- **Phase 1:** FastAPI, Local Auth, PostgreSQL (`navixa_db`), AWS Collector (NAVIXA Discover), Basic Validation (NAVIXA Validate)
- **Phase 2:** Azure/GCP/OCI Collectors, React UI, Visualization (NAVIXA Topology)
- **Phase 3:** Neo4j (`navixa_graph`), Internet Path Analysis (NAVIXA Pathfinder), Async Processing
- **Phase 4:** Claude/GPT/Azure OpenAI/Gemini/Bedrock Integration (NAVIXA InsightAI), Reporting (NAVIXA Reports)
- **Phase 5:** Enterprise SSO, Scaling, Production Hardening, NAVIXA Watch groundwork

---

## 21. Expected Outcome

Design and implement **NAVIXA AI** as an enterprise-grade SaaS-ready platform capable of providing complete multi-cloud network architecture visibility, Hub-and-Spoke validation, internet exposure analytics, graph-based network intelligence, AI-powered audit findings, topology visualization, and executive reporting across AWS, Azure, GCP, and OCI.

---

## 22. Final Requirement

Generate complete software architecture, database schema, API design, backlog, sprint plan, environment setup, and starter codebase structure following enterprise-grade software engineering practices — consistently branded as **NAVIXA AI** across UI, documentation, repository, and database naming.

**Instructions for Claude Code:**
1. Start by proposing the high-level software architecture (component diagram, data flow) based on the requirements above, using NAVIXA module naming (Discover, Topology, Pathfinder, Validate, Graph, InsightAI, Reports).
2. Design the PostgreSQL (`navixa_db`) schema (tables for tenants, users, roles, audit jobs, findings, evidence) and the Neo4j (`navixa_graph`) graph schema (node/relationship types matching the Data Normalization model).
3. Design the REST API (FastAPI routes, request/response models) covering auth, tenant registry, audit jobs, collectors, findings, and reports — with route/tag naming aligned to NAVIXA modules where sensible.
4. Produce a product backlog broken into epics and user stories aligned to the Development Roadmap phases above.
5. Produce a sprint plan (assume 2-week sprints) for Phase 1 in detail, with subsequent phases at a higher level.
6. Scaffold the starter codebase following the Recommended Project Structure (`navixa-ai` repo), starting with Phase 1 scope: FastAPI app skeleton, local JWT auth, PostgreSQL models via SQLAlchemy + Alembic migrations, AWS collector stub (NAVIXA Discover) built with the async/concurrent design described in Section 10a, and basic Hub-and-Spoke validation logic (NAVIXA Validate).
7. Provide environment setup instructions (Docker Compose for PostgreSQL, Redis, Neo4j, backend, and frontend; `.env.example` file; `requirements.txt`), including the `navixa_db`, `navixa_graph`, and `navixa_cache` database/service names.
8. Apply NAVIXA AI branding consistently: login screen, dashboard header, and documentation header copy exactly as specified in Section 1.

Work incrementally, confirming scope before generating large amounts of code, follow the Security Requirements strictly (no hardcoded secrets, no frontend access to secrets, all cloud/AI calls routed through backend services), and commit work following the Version Control & Repo Setup conventions in Section 19a (branch naming, Conventional Commits, one logical unit of work per commit).
