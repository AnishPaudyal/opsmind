# Phase 8C Authenticated Frontend and Full-Stack Product Gate

## Gate status

- Status: Accepted
- Proposed: 2026-08-13
- Review/acceptance date: 2026-08-13
- Governed by:
  [#77](https://github.com/AnishPaudyal/opsmind/issues/77)
- Owner: Anish Paudyal
- Decision: Accepted
- Implementation authorization: Batch 1 only, effective after this gate PR
  merges to canonical `main`
- Governing decision:
  [ADR-0007](decisions/0007-select-phase-8-zero-cost-cloud-deployment-and-product-delivery-architecture.md)
- Canonical baseline: `77b4f1d8981fe998fe55a8bf6e3dea2f99e02dfd`

Phase 8A and Phase 8B are Complete. Phase 8 overall remains Current. This
accepted gate defines the Phase 8C implementation and live-delivery boundary.
Batch 1 implementation is authorized only after this gate PR merges to
canonical `main`; every later batch and live mutation remains separately gated.

## Goal

Turn the deployed OpsMind backend into the first usable full-stack product:

```text
product
-> inventory
-> demand history
-> forecast
-> stockout exposure
-> reorder recommendation
-> review
-> approve or reject
-> audit history
```

An authenticated user should be able to understand and operate that complete
workflow from a clear static browser application while the existing FastAPI
authorization, PostgreSQL persistence, release, and provider-ownership
boundaries remain authoritative.

## Canonical audit

The gate audit examined repository governance, accepted ADRs, Phase 8A
container/runtime design, the Phase 8B gate and accepted review, every FastAPI
router and public schema, repository Protocols and PostgreSQL/memory
implementations, authentication and trusted-principal mapping, application
composition, OpenAPI, tests, Docker and Render contracts, ZITADEL Terraform,
GitHub workflows, and current documentation/tooling conventions.

The baseline establishes:

- no frontend source, Node package manifest, JavaScript/TypeScript toolchain,
  or Cloudflare resource exists;
- accepted ADR-0007 selects React, TypeScript, Vite, React Router, TanStack
  Query, an OpenAPI-derived client, a restrained chart library, and Cloudflare
  Pages Free; it explicitly does not select Next.js because no SSR requirement
  exists;
- the deployed API is `https://opsmind-api-ru63.onrender.com`, with business
  routes under `/api/v1` and public `/health` and `/ready` probes;
- every business route requires a bearer access token and exactly one current
  action permission; `/health`, `/ready`, OpenAPI, Swagger UI, and ReDoc remain
  public;
- the public ZITADEL User Agent application uses Authorization Code, no client
  authentication, JWT access tokens, and explicit role scopes;
- Terraform currently grants only `opsmind.business.read` to the machine-only
  release-smoke identity. It does not grant a human user any OpsMind project
  role, so a live interactive browser user is not yet authorized for the
  product workflow;
- the Phase 8C repository packet replaces ZITADEL's localhost callback, logout,
  and origin defaults with the captured Pages origin and sets
  `dev_mode = false`; a separately authorized HCP apply is still required before
  the live client changes. Current ZITADEL guidance requires production HTTPS
  applications to disable development mode;
- the backend has a tested exact-origin CORS setting and middleware, but the
  live Render service does not receive the production origin until a separately
  authorized Blueprint synchronization and protected release;
- the existing review API retrieves a stored recommendation only by UUID and
  has no collection route or repository list operation;
- the accepted Phase 8B live service, protected release, Neon schema, GHCR
  image, ZITADEL project, and HCP state are inputs, not resources for the
  frontend to replace or manage.

There is no separate Phase 8A review file. The authoritative Phase 8A evidence
is the accepted ADR-0007 direction, the
[Phase 8A container delivery contract](phase-8a-container-delivery.md), and the
canonical Phase 8A/8B status and review records.

## Actual browser-relevant API

All versioned routes below use `Authorization: Bearer <access-token>`. A missing
or invalid credential returns the existing generic `401` with a Bearer
challenge. An authenticated principal without the exact required permission
receives the existing generic `403`. Path, query, and request-model validation
can produce `422` in addition to the explicit domain responses listed.

| Method | Path | Request | Response | Permission | Important outcomes | Persistent mutation |
| --- | --- | --- | --- | --- | --- | --- |
| `POST` | `/api/v1/products` | `ProductCreateRequest` | `ProductResponse` | `business:write` | `201`; `409` normalized SKU duplicate; `422` invalid product | Creates product |
| `GET` | `/api/v1/products` | None | `ProductResponse[]` | `business:read` | `200`; canonical SKU order | No |
| `GET` | `/api/v1/products/{product_id}` | UUID path | `ProductResponse` | `business:read` | `200`; `404` product; `422` UUID | No |
| `PUT` | `/api/v1/products/{product_id}/inventory` | `InventorySetRequest` | `InventoryResponse` | `business:write` | `200`; `404` product; `422` quantities/UUID | Sets or replaces inventory |
| `GET` | `/api/v1/products/{product_id}/inventory` | UUID path | `InventoryResponse` | `business:read` | `200`; `404` product or inventory; `422` UUID | No |
| `POST` | `/api/v1/products/{product_id}/demand` | `DemandBatchCreate` | `DemandObservationResponse[]` | `business:write` | `201`; `404` product; `409` duplicate product/date; `422` invalid/empty batch | Atomically appends batch |
| `GET` | `/api/v1/products/{product_id}/demand` | Optional inclusive `start_date`, `end_date` | `DemandObservationResponse[]` | `business:read` | `200` chronological; `404` product; `422` invalid/reversed range | No |
| `GET` | `/api/v1/products/{product_id}/forecast` | `lookback_observations=7`, `horizon_days=7`, optional inclusive `as_of_date`; counts are `1..365` | `ForecastResponse` | `business:read` | `200`; `404` product; `422` invalid or insufficient eligible demand | No |
| `GET` | `/api/v1/products/{product_id}/stockout-exposure` | `lookback_observations=7`, optional inclusive `as_of_date` | `StockoutExposureResponse` | `business:read` | `200`; `404` product/inventory; `422` invalid or insufficient demand | No |
| `GET` | `/api/v1/products/{product_id}/reorder-recommendation` | `lookback_observations=7`, optional inclusive `as_of_date` | `ReorderRecommendationResponse` | `business:read` | `200`; `404` product/inventory; `422` invalid or insufficient demand | No |
| `POST` | `/api/v1/products/{product_id}/reorder-recommendations` | Query parameters as above; no body | `ReorderRecommendationReviewResponse` | `business:write` | `201`; `404` product/inventory; `409` no actionable recommendation or duplicate; `422` invalid/history | Atomically stores review and creation event |
| `GET` | `/api/v1/reorder-recommendations/{recommendation_id}` | UUID path | `ReorderRecommendationReviewResponse` | `business:read` | `200`; `404` review; `422` UUID | No |
| `POST` | `/api/v1/reorder-recommendations/{recommendation_id}/approve` | `ApproveRecommendationRequest` | `ReorderRecommendationReviewResponse` | `recommendation:decide` | `200`; `404` review; `409` conflicting terminal state; `422` invalid details | Atomically approves and audits |
| `POST` | `/api/v1/reorder-recommendations/{recommendation_id}/reject` | `RejectRecommendationRequest` | `ReorderRecommendationReviewResponse` | `recommendation:decide` | `200`; `404` review; `409` conflicting terminal state; `422` invalid reason | Atomically rejects and audits |
| `GET` | `/api/v1/reorder-recommendations/{recommendation_id}/audit-events` | UUID path | `RecommendationAuditHistoryResponse` | `business:read` | `200` sequence order; `404` review; `422` UUID | No |
| `GET` | `/health` | None | `HealthResponse` | Public | `200`; process liveness only; may expose revision header | No |
| `GET` | `/ready` | None | `ReadinessResponse` | Public | `200` ready or bounded `503`; PostgreSQL connectivity/revision in current deployment | No |

### Schema details that shape the UI

- `ProductCreateRequest`: nonblank `sku`, `name`, and `unit_of_measure`;
  non-negative integer `lead_time_days`; `is_active` defaults true. The server
  trims text and centralizes uppercase SKU normalization.
- `InventorySetRequest`: non-negative integer `on_hand_quantity` and
  `allocated_quantity`; returned `available_quantity` may be negative.
- `DemandBatchCreate`: a nonempty atomic list of `{demand_date, quantity}`;
  quantity is a strict non-negative integer and recorded zero is meaningful.
- Forecasts use a recent-observation count, not calendar-day imputation, and
  expose deterministic simple-mean evidence and two-decimal public values.
- Exposure is deterministic evidence, not a probability. Reorder quantity is
  a whole-unit ceiling of the normalized projected shortage.
- A review contains an immutable recommendation/evidence snapshot, one of
  `pending_review`, `approved`, or `rejected`, and an optional terminal
  decision. Approval quantity is an optional strict integer of at least one and
  defaults to the recommendation; its note is optional. Rejection requires a
  nonblank reason.
- The terminal actor comes only from the trusted principal. The browser never
  submits `decided_by`.
- Audit events are ordered by per-recommendation sequence and remain audited
  state storage, not event sourcing or a compliance-grade ledger.

## Backend gap classification

### Required blocker

Add one collection capability:

```text
GET /api/v1/reorder-recommendations
permission: business:read
optional filters: review_status, product_id
response: ReorderRecommendationReviewResponse[]
ordering: created_at descending, then recommendation_id as deterministic tie-break
```

The implementation must extend the existing `RecommendationWorkflowRepository`
Protocol and both memory and PostgreSQL implementations, use the stored
aggregate without recalculation, and preserve cross-application PostgreSQL
behavior. Exact enum/UUID filters return the normal `422` on invalid input.

This is a blocker because the current API requires an already-known review UUID.
After navigation, reload, or a new browser session, the SPA cannot reconstruct
a persisted pending-review queue or show recommendations requiring attention.

### Required live identity prerequisite

This is not a missing backend capability, but it blocks live authenticated
acceptance. The owner must create or identify one dedicated human portfolio
operator in the OpsMind ZITADEL organization. Terraform then manages exactly
one project grant for that public user ID containing:

```text
opsmind.business.read
opsmind.business.write
opsmind.recommendation.decide
```

The human account and its authentication/MFA remain owner-controlled. Terraform
does not create a password, private key, session, IAM/ORG/PROJECT owner role, or
other administrator grant. Reusing the organization owner as the permanent
product authorization model is rejected even though the backend would ignore
unmapped admin claims. The existing release-smoke machine identity and its
read-only grant remain unchanged.

### Useful conveniences, not blockers

- dashboard aggregation;
- bulk inventory, demand, forecast, exposure, or recommendation reads;
- server-side product search, sorting, or pagination;
- a global audit-event feed.

The bounded portfolio dataset can derive an overview from the product list,
review list, and per-product reads. Those convenience endpoints do not justify
expanding the backend in Phase 8C.

The OpenAPI description for `RecommendationAuditEventResponse.actor` still
calls the actor caller-supplied even though accepted ADR-0006 and the current
route derive terminal actors from `TrustedPrincipal`. Correct that stale schema
description in Batch 2. It is a documentation/contract-hygiene defect, not a
missing runtime capability.

### Future enhancements

Product editing/deactivation operations, bulk import, calibrated risk,
probabilistic or trained forecasts, ordering integration, global audit search,
multi-tenancy, and real-time updates remain future work.

## Selected frontend architecture

| Concern | Proposed choice | Reason |
| --- | --- | --- |
| Application | Static React SPA | Matches ADR-0007, browser OIDC, and Pages; no server runtime is required. |
| Language | Strict TypeScript | Contract safety and portfolio value without a second server language. |
| Build | Vite | Native static SPA output; Cloudflare's documented React/Vite contract is `npm run build` to `dist`. |
| Runtime toolchain | Node.js 24 LTS, npm, committed `package-lock.json` | Node 24 is the current LTS line at proposal time; npm avoids another package-manager bootstrap. Exact versions are locked in implementation. |
| Routing | React Router | Explicit callback, protected shell, product, and review deep links with Pages SPA fallback. |
| Server state | TanStack Query | Handles bounded caching, invalidation, and loading/error state without a general client-state store. Mutations use retries disabled. |
| API | `openapi-typescript` plus `openapi-fetch` | Small OpenAPI-derived types/client, deterministic regeneration, and no handwritten duplicate response models. |
| OIDC | `oidc-client-ts` behind an OpsMind adapter | Browser-focused Authorization Code + PKCE support, callback/state validation, token events, and logout without a framework-specific auth server. |
| Forms | React Hook Form + Zod at the form boundary | Accessible forms and immediate usability checks; backend errors remain authoritative. |
| Charts | Recharts, one dependency | A restrained React chart for demand/forecast evidence; accessible tables/text remain authoritative. |
| Component tests | Vitest, React Testing Library, user-event, MSW | Vite-native, user-visible component behavior with deterministic API/OIDC boundaries. |
| Browser tests | A small Playwright suite | Adds value for routing, callback, protected navigation, and the full mocked workflow; no brittle automation of third-party login pages. |
| Code quality | ESLint flat config, Prettier, `tsc --noEmit` | Conventional React/TypeScript checks, strict types, and deterministic formatting. |
| Delivery | Cloudflare Pages Free Git integration | Static CDN/HTTPS deployment from `main`; no Functions, Workers, SSR, or server secret. |

Next.js, Remix, server components, and SSR are rejected for this slice: they
would introduce server/runtime ownership and Pages adaptation without a product,
security, SEO, or performance requirement. Redux is unnecessary because remote
state belongs in TanStack Query and bounded local state belongs in React.

Implementation must review exact dependency versions, lock them, check licenses
and advisories, and avoid packages beyond the roles above. The gate selects
responsibilities, not an unbounded starter template.

## Project layout and contract generation

The proposed top-level shape is:

```text
frontend/
├── public/
│   ├── _headers
│   └── static assets
├── src/
│   ├── api/
│   ├── auth/
│   ├── components/
│   ├── features/
│   ├── routes/
│   ├── test/
│   └── styles/
├── tests/e2e/
├── package.json
├── package-lock.json
├── tsconfig*.json
├── vite.config.ts
└── playwright.config.ts
```

A repository script exports the FastAPI OpenAPI document deterministically and
generates a checked TypeScript schema. CI regenerates it and requires an empty
diff. The fetch adapter adds the current access token, `Accept`, and bounded
request ID; parses the documented JSON errors; exposes response request/revision
headers; never logs tokens; and never automatically retries a mutation.

## User experience and route map

| Browser route | User outcome | Primary actions and states |
| --- | --- | --- |
| `/login` | Understand OpsMind and begin authentication | Sign in; public readiness/cold-wake state; bounded provider error. |
| `/auth/callback` | Complete the code exchange | Progress, exact callback failure, safe restart, restore pre-login route. |
| `/` | Operational overview | Readiness, product count, pending reviews, shortage/reorder attention derived from real API data; links to action. |
| `/products` | Browse products | Normalized-SKU table; create product only for `business:write`; empty and load errors. |
| `/products/:productId` | Operate one product workflow | Product facts; set inventory; add demand batch; inspect history/forecast/exposure/recommendation; create a review only when actionable. |
| `/recommendations` | Reconstruct and filter stored reviews | Pending/approved/rejected and optional product filters; deterministic queue; empty state. |
| `/recommendations/:recommendationId` | Review immutable evidence and history | Evidence, approve/reject for `recommendation:decide`, conflict-safe terminal result, ordered audit. |
| `/forbidden` | Explain insufficient permission | No false not-found behavior; safe navigation/logout. |
| `/unavailable` | Explain backend cold wake or outage | Bounded retry for readiness/safe reads, request ID/revision when available. |
| unmatched | Explain client route not found | Return to overview; Pages still serves SPA shell. |

The product detail page is one composed workspace rather than separate routes
for every endpoint. Sections preserve the sequence: inventory and demand inputs,
then transparent forecast and exposure, then calculation and review creation.
This keeps the page set small without hiding the evidence chain.

### Role-aware behavior

- `opsmind.business.read`: can load every read surface and audit history.
- `opsmind.business.write`: can create products, set inventory, add demand, and
  store an actionable recommendation review.
- `opsmind.recommendation.decide`: can approve or reject a pending review.
- Roles do not imply one another. The UI shows actions only when their exact
  role is present, but a direct call still depends entirely on FastAPI.
- Unknown/malformed role claims grant no visible action. A principal with no
  mapped role sees a clear not-authorized state after the backend's `403`.

### State and error behavior

- Skeleton/progress UI is bounded and labeled; previous data may remain visible
  as stale during a safe refresh.
- Empty states explain the next valid action: create a product, set inventory,
  add demand, or wait until a shortage makes a recommendation actionable.
- Client form validation mirrors only public shape constraints; `422` details
  are mapped to fields when possible and otherwise shown as a safe summary.
- `404` distinguishes missing product, inventory, or review using the endpoint
  context. `409` preserves the server detail and refreshes the relevant review
  or data; it never blindly replays.
- A `401` removes the local OIDC user and offers one controlled sign-in redirect
  while retaining the intended route in OIDC state. It does not create a retry
  loop.
- A `403` retains authentication and explains the missing action capability.
- Unexpected errors show a bounded message and response request ID. Token,
  provider payload, stack, or secret details never enter the UI or logs.
- Only readiness and idempotent reads use bounded backoff for the Free service
  wake contract. No `POST` or `PUT` is automatically retried.
- Browser refresh and deep links work through Pages SPA fallback; server state
  is reloaded from the API, never treated as durable browser state.

## Exact browser authentication flow

Public identifiers already established by Phase 8B:

```text
issuer = https://opsmind-phase-8b-gl9aih.us1.zitadel.cloud
client_id = 386124342116795580
```

The project ID/audience is also public but must be taken from the existing safe
HCP Terraform `project_id` output at the owner boundary. It is not guessed or
copied from a secret.

1. The SPA validates its public build configuration before rendering protected
   routes.
2. Sign in calls `signinRedirect` with `response_type=code`, PKCE enabled with
   S256, the exact registered callback, and state containing only a bounded
   return path.
3. Scopes are exactly:
   - `openid`;
   - `profile` for bounded display identity;
   - `urn:zitadel:iam:org:project:id:{project_id}:aud` for the exact API
     audience; and
   - `urn:zitadel:iam:org:projects:roles` for project role claims.
4. `offline_access` is not requested. The initial slice has no refresh-token or
   long-lived browser-token requirement.
5. The live ZITADEL application replaces the Phase 8B localhost placeholders
   with the exact HTTPS Pages callback, root post-logout URI, and origin, and
   sets `dev_mode = false`. Local component/browser tests use deterministic
   auth fixtures; Phase 8C does not weaken the live client to support HTTP
   localhost. A separate live development client would require later review.
6. ZITADEL authenticates the user and redirects to `/auth/callback`. The OIDC
   library validates stored state, nonce/protocol response, and PKCE verifier,
   exchanges the code, and clears stale transaction state.
7. The access token is held through the library's `sessionStorage` user store;
   transaction state is also constrained to `sessionStorage`. Nothing is copied
   to `localStorage`, cookies, application logs, analytics, URLs, or React query
   cache.
8. API calls send `Authorization: Bearer <access_token>` with fetch credentials
   omitted. FastAPI performs signature, issuer, audience, time, token-type,
   subject, and exact project-role validation through the existing JWKS path.
9. The SPA may decode the access token only to improve navigation/action
   visibility. It must not claim that client-side decoding authorizes anything.
10. Automatic silent renew is disabled initially. Expiry or API `401` removes
   local state and offers an interactive redirect. This avoids hidden iframe,
   third-party-cookie, and unbounded retry behavior. A later refresh-token
   design requires separate review.
11. Logout removes the local user and uses ZITADEL's end-session redirect with
    the registered exact root post-logout URI and library-held ID token hint
    when supported. Callback/logout failures remain bounded and fail closed.

All of the following Vite values are intentionally public and are visible in
the static bundle:

```text
VITE_OPSMIND_API_BASE_URL
VITE_OPSMIND_ENVIRONMENT
VITE_OPSMIND_ZITADEL_ISSUER
VITE_OPSMIND_ZITADEL_PROJECT_ID
VITE_OPSMIND_ZITADEL_CLIENT_ID
```

Redirect and post-logout URIs are derived from the validated browser origin plus
fixed `/auth/callback` and `/` paths. No password, database URL, private key,
client secret, token, deploy hook, HCP credential, or reusable provider secret
may use a `VITE_` name. Vite documents that every `VITE_*` value is bundled and
public.

## Exact CORS integration

Phase 8C adds a typed `OPSMIND_CORS_ALLOWED_ORIGINS` setting. Its external form
is a JSON array of exact serialized origins. Validation must reject:

- `*`, origin regexes, paths, queries, fragments, userinfo, or credentials;
- non-HTTP(S) schemes;
- duplicates after normalization;
- HTTP origins outside explicitly configured local development; and
- any implicit production default.

When the list is empty, no CORS middleware is installed and current non-browser
behavior remains unchanged. Production configuration contains only the captured
stable `https://<project>.pages.dev` origin. Local development explicitly uses
`http://localhost:5173`; it is not hard-coded into production.

The middleware contract is:

```text
allow_origins: exact configured values
allow_methods: GET, POST, PUT, OPTIONS
allow_headers: Authorization, Content-Type, X-Request-ID
expose_headers: X-Request-ID, X-OpsMind-Revision
allow_credentials: false
max_age: 600
```

The SPA uses a bearer header, not cookies or HTTP-auth credentials, and fetches
with `credentials: "omit"`. The explicit `Authorization` header triggers CORS
preflight; it is allowed directly. `allow_credentials=false` is therefore the
narrow cookie-free policy. `OPTIONS` is handled by the middleware and is not a
new business route.

Tests cover allowed/rejected preflight and simple requests, exact methods and
headers, exposed response headers, no credentials header, public probes,
business authentication, custom API prefixes, middleware ordering, and
unexpected errors. No wildcard origin or wildcard header/method is accepted.

### Production-origin bootstrap

At gate acceptance, the final Pages URL did not exist and could not be guessed.
Batch 3 Substep 3 has since captured the provider-issued dormant-project origin
`https://opsmind-app.pages.dev`; no frontend deployment exists. The governed
sequence remains:

1. merge the credential-free static application and tested configurable CORS;
2. owner creates/connects the reviewed Free Pages project and captures its
   actual stable `pages.dev` origin;
3. commit the public exact origin to reviewed Cloudflare/ZITADEL/Render
   configuration where appropriate;
4. apply the reviewed ZITADEL replacement of localhost redirect/logout/origin
   values and `dev_mode = false` through HCP, then use the existing protected
   backend release for CORS;
5. deploy the frontend with the exact public identifiers; and
6. perform live browser evidence.

Batch 3 Substep 4 implements item 3 as a repository-only review packet using
`https://opsmind-app.pages.dev`. It does not execute the HCP plan/apply in item
4, synchronize or release Render, enable Cloudflare production deployment, or
perform live browser evidence. Those actions remain Substeps 5–8 and require
separate owner authorization.

Preview deployments are disabled initially. Random preview subdomains are not
added through a wildcard or regex to ZITADEL or CORS. A preview may use mocked
API data in CI, or a later exact stable preview origin may be separately
reviewed.

## Cloudflare Pages Free design

The proposed production contract is:

| Setting | Value |
| --- | --- |
| Offering | Cloudflare Pages Free only |
| Project | One stable OpsMind frontend project; final available name verified at bootstrap |
| Source | `AnishPaudyal/opsmind` through owner-approved GitHub integration |
| Production branch | `main` |
| Root directory | `frontend` |
| Build command | `npm run build` |
| Output directory | `dist` |
| Runtime | Static assets only; no Pages Functions or Workers |
| Preview deployments | Disabled initially |
| Domain | Provider-issued stable `pages.dev`; no purchased custom domain |
| Public build values | Exact five `VITE_*` values above, all plain text |

Cloudflare's current official Free limits are 500 builds per month, one
concurrent build, a 20-minute build timeout, 20,000 files, and 25 MiB per asset.
The build and artifact must remain comfortably inside those limits. Any payment
method requirement, paid plan, Workers/Functions billing, automatic paid
upgrade, custom-domain purchase, or limit that makes the static site nonviable
is a stop condition.

Cloudflare automatically treats a static site with no top-level `404.html` as
an SPA and serves the root document for unmatched routes. Implementation must
verify this behavior against deep links and may add a reviewed `_redirects`
fallback only if current platform evidence requires it.

`frontend/public/_headers` supplies at least:

- `Content-Security-Policy` limited to the Pages origin, the exact ZITADEL
  issuer endpoints required by the OIDC library, and the exact Render API;
- `X-Frame-Options: DENY` or equivalent CSP `frame-ancestors 'none'`;
- `X-Content-Type-Options: nosniff`;
- a strict `Referrer-Policy`;
- a minimal `Permissions-Policy`; and
- no permissive static-asset CORS rule.

The final CSP is generated from exact public origins and tested in the deployed
site. It must not contain `unsafe-eval`; any narrowly required style exception
must be justified by implementation evidence.

### Cloudflare ownership and owner boundary

ADR-0007 assigns provider-supported Cloudflare resources to Terraform with HCP
Terraform state. Current official provider evidence exposes a Pages project,
build configuration, Git source/branch controls, preview controls, and plain
build environment values. The proposed repository layout is `infra/cloudflare`
with a pinned reviewed official provider and a separate VCS-driven HCP
workspace because the existing `infra/zitadel` workspace already owns live
state with a distinct working directory.

Owner-only bootstrap is limited to:

1. create/authenticate a Cloudflare Free account and confirm no payment method
   or paid upgrade is required;
2. connect Cloudflare's GitHub integration to this repository only, which the
   provider requires before a Pages `source` block can be used;
3. create the separate HCP workspace pointing to `infra/cloudflare`;
4. enter the Cloudflare account ID as non-sensitive and a narrowly scoped Pages
   Read/Write API token as a sensitive write-only HCP variable;
5. review the first plan for exactly the bounded Pages project and no unrelated
   account/zone/Worker resource; and
6. explicitly approve apply and later exact public URL handoff.

Terraform must not manage ZITADEL bootstrap identity, Neon, Render, GHCR, a
custom domain, DNS zone, Workers, Pages Functions, access policy, or secrets.
The new workspace does not share remote state and stays within HCP Free limits.
If the current provider cannot represent the reviewed Git integration without
broader authority or destructive drift, stop and return to owner review rather
than creating an overlapping manual resource.

## Validation strategy

### Deterministic repository checks

- npm clean install from the committed lockfile;
- Prettier check, ESLint, strict `tsc --noEmit`, Vitest/component coverage, and
  production Vite build;
- deterministic FastAPI OpenAPI export and generated TypeScript diff check;
- Playwright install pinned by the lockfile and a small Chromium workflow for
  user-visible protected routing and complete mocked operations;
- Terraform format, locked backendless initialization, validation, and exact
  provider checks for `infra/cloudflare` without live credentials;
- all existing repository, Render schema, Terraform, container, Python,
  PostgreSQL integration, strict mypy, Ruff, pytest, and 95% combined-coverage
  gates;
- Markdown links, empty-file, secret-pattern, generated-artifact, dependency,
  and lockfile checks.

Frontend CI is a separate least-privilege workflow triggered only by frontend,
OpenAPI contract, and its workflow/config inputs where GitHub supports path
filters. It pins actions to full commits, uses `contents: read`, performs no
cloud mutation, and does not receive credentials.

### Frontend and auth tests

- public config validation and refusal to start on missing/malformed values;
- login redirect settings, PKCE enabled, exact scopes, bounded return path,
  callback success/failure, state cleanup, expiry, 401, 403, and logout;
- no token in URL, log, rendered error, query cache, fixture, or snapshot;
- exact roles control visible actions without being treated as authorization;
- request adapter adds Bearer and request ID, maps 404/409/422, exposes request
  correlation, and does not retry mutations;
- loading, empty, stale, conflict, forbidden, unavailable, and not-found states;
- accessible forms, keyboard flow, focus management, semantic names, tables,
  and chart text alternatives;
- the complete mocked product-to-audit workflow in one maintainable browser
  test without driving ZITADEL's hosted UI.

### Backend integration tests

- list-reviews Protocol contract in memory and PostgreSQL;
- deterministic filter/order, isolation, sharing, restart durability, and no
  recalculation/mutation;
- collection route authentication, exact permission, filters, empty state,
  malformed values, custom prefix, and OpenAPI;
- exact CORS allowed/rejected origin, method, header, preflight, credentials,
  exposed header, error, and public-probe behavior;
- full existing product, inventory, demand, calculation, review, audit,
  security, health/readiness, migration, and persistence regressions.

### Live acceptance evidence

- Cloudflare plan is Free, project is one static site, source/settings match the
  reviewed Terraform state, preview is disabled, and no paid resource exists;
- production deployment identifies the exact `main` commit, build command,
  output, stable URL, headers, asset count/size, and rollback target;
- exact ZITADEL callback, post-logout, origin, public client, PKCE, audience, and
  role scopes, plus one non-admin human operator grant with the exact three
  project roles;
- public shell and readiness/wake behavior without authentication;
- owner-controlled interactive login, then live read, write, review creation,
  approve/reject, audit, reload, and logout using synthetic portfolio data;
- Neon-backed state survives browser reload and an API service wake/restart;
- a missing permission produces `403`, an expired/removed session produces the
  bounded reauthentication path, and no mutation is replayed;
- browser request ID correlates with API response/release evidence;
- no token or credential appears in browser logs, GitHub logs, repository,
  screenshot, Terraform output/state inspection, or chat.

Live authentication is an owner-controlled manual acceptance step. Ordinary CI
does not store an interactive owner password/MFA credential and does not scrape
the third-party ZITADEL login UI.

## Accelerated implementation batches

Phase 8C should use three broad, self-validating PRs rather than fragmented
micro-workstreams.

### Batch 1 — frontend, contract, auth, and quality foundation

Scope:

- `frontend/` Node/npm/Vite/React/TypeScript foundation;
- design tokens, responsive shell, router, public login, callback, protected
  route, logout, and bounded error pages;
- public config validation, `oidc-client-ts` adapter, exact scopes, session
  storage, role projection, and token-aware API wrapper;
- deterministic OpenAPI export/generated schema/client;
- TanStack Query provider, MSW fixtures, baseline accessible components;
- unit/component/browser foundation, coverage, build, and credential-free
  frontend CI;
- minimal README/CONTRIBUTING/tooling documentation.

Likely files: `frontend/**`, OpenAPI export/check script, `.gitignore`,
`.github/workflows/frontend-quality.yml`, README, CONTRIBUTING, and narrowly
required repository checks.

Merge criteria: complete deterministic frontend gate, no live provider change,
no secret, callback/logout behavior mocked and tested, OpenAPI regeneration
clean, existing backend checks green.

Stopping condition: any requirement for SSR, a browser secret, a broad scope,
or an unreviewed dependency returns to design.

Owner boundary: dependency/toolchain review and merge only; no Cloudflare or
ZITADEL action.

### Batch 2 — operational workflow, review-list blocker, and CORS

Scope:

- repository Protocol, memory/PostgreSQL, route/schema/OpenAPI/tests for the
  single review-list blocker;
- typed CORS setting, validation, middleware integration, Render configuration
  shape, and full CORS tests;
- overview, products, product detail, inventory, demand, forecast, exposure,
  reorder, review queue/detail, approve/reject, audit, chart, loading, empty,
  validation, conflict, authorization, wake, and request-ID UX;
- complete mocked browser workflow and full Python/PostgreSQL regression.

Likely files: bounded `src/opsmind` repository/route/schema/config/application
files and tests; `frontend/src/features/**`, routes/components/tests; generated
OpenAPI client; `render.yaml`; operational documentation.

Merge criteria: all local and hosted frontend/backend/contract/CORS checks pass;
the entire product-to-audit workflow works against deterministic fixtures; no
live origin is guessed; no mutation retries.

Stopping condition: broader backend redesign, unsafe CORS, schema migration
outside the reviewed list capability, or authorization weakening.

Owner boundary: approve the backend API/CORS/public configuration contract and
merge; no live Pages or ZITADEL change yet.

### Batch 3 — Cloudflare delivery, exact-origin wiring, live proof, and review

Scope:

- pinned `infra/cloudflare` configuration, credential-free Terraform CI, HCP
  workspace/runbook, static security headers, and delivery documentation;
- owner Cloudflare/GitHub/HCP bootstrap and first reviewed plan/apply;
- capture actual stable Pages URL;
- owner creation or selection of one dedicated human portfolio operator and a
  reviewed Terraform project grant containing exactly the three OpsMind roles;
- reviewed ZITADEL production redirect/logout/origin variables and HCP plan/apply;
- exact production CORS configuration and existing protected backend release;
- production Pages deploy from `main`, live authenticated workflow, persistence,
  cold-wake, correlation, rollback, cost/security evidence;
- Phase 8C review and status reconciliation.

Likely files: `infra/cloudflare/**`, `infra/zitadel/**`, `render.yaml`, frontend
public config/header documentation, Terraform/front-end workflows as required,
the Phase 8C review, and current governance/status files.

Merge criteria: all hosted checks green; HCP plans contain only reviewed
resources; both applies succeed; Free/no-payment state verified; exact callback
and CORS evidence; deployed full workflow passes; limitations documented.

Stopping condition: payment, paid/auto-upgrade requirement, broader provider
token, drift/destruction, unexpected cloud resource, secret exposure, or failed
security/auth contract.

Owner boundary: account/GitHub connection, HCP variables and apply approval,
interactive ZITADEL login, exact URL handoff, deployment review, live smoke, and
formal Phase 8C acceptance. Codex must stop at each separately authorized live
mutation boundary.

Substep 4 is the repository-only exact-origin packet. It may update reviewed
ZITADEL source, the Render Blueprint value, backend CORS validation, tests,
governance checks, and durable documentation. It must stop before merge if that
merge could queue the Substep 5 credentialed ZITADEL plan. Substep 5 begins the
owner-controlled human operator and HCP ZITADEL plan/apply boundary.

Substep 4 is Complete through PR #86 and canonical commit
`18d29c92dd0070faad8038c88d159d533ad353e8`. HCP run
`run-UXDXd9rKDhe74ocK` verified the source as an unapplied, in-place origin-only
proposal with zero additions, one change, zero destroys, and zero replacements.

Substep 5 starts with repository preparation for exactly one
`zitadel_user_grant` referencing the public numeric ID of an existing human in
the OpsMind organization. The owner creates or selects that dedicated,
MFA-protected portfolio operator outside Terraform, verifies that it is not the
organization-owner identity and has no `IAM_OWNER`, `ORG_OWNER`,
`PROJECT_OWNER`, or other administrative authority, and shares only its public
user ID through the governed HCP variable boundary. Password/passkey material,
MFA secrets or codes, recovery material, browser sessions, access/refresh
tokens, private keys, and personal account details never enter Terraform, Git,
CI, logs, screenshots, or chat.

Terraform grants that existing same-organization user exactly
`opsmind.business.read`, `opsmind.business.write`, and
`opsmind.recommendation.decide`. It does not create the user, an administrator
role, a credential, a machine identity/key, or a cross-organization
`zitadel_project_grant`. The existing project, public SPA client and identity,
three role definitions, `opsmind-release-smoke` identity/read-only grant, and
external `opsmind-terraform` bootstrap identity/key remain unchanged.

The origin-only run stays Pending confirmation and unapplied during repository
preparation. After the operator-grant source merges, the owner supplies only the
public user ID as a fourth nonsensitive HCP Terraform variable, verifies that a
future run captures the merged configuration and four-variable set, separately
authorizes discarding the older origin-only run, and allows exactly one combined
plan. The only acceptable combined plan is one grant addition, one in-place SPA
change, zero destroys, and zero replacements. Stop on any destruction,
replacement, project/application recreation, client-ID change, role-definition
or smoke/bootstrap identity change, user creation, administrator role,
cross-organization grant, unrelated drift, or more than one addition/change.
Apply remains a separate owner decision.

## Security, cost, and scope constraints

- No browser secret, database access, cookie/session backend, token logging,
  local-storage token, hidden credential, client-secret flow, or implicit flow.
- No wildcard CORS, wildcard preview origin, role inheritance, client-only
  authorization, unknown-role grant, or broad admin role.
- No Pages Function, Worker, KV, D1, R2, custom domain, paid Cloudflare feature,
  or automatic upgrade.
- No change to Neon ownership, migration authority, Render Free shape, GHCR
  identity, HCP/ZITADEL bootstrap identity, or protected cloud-release contract
  except separately reviewed Phase 8C configuration inputs.
- No production-readiness, HA/DR, compliance, calibrated-risk, model-quality,
  cost-savings, or AWS-deployment claim.
- No microservices, Kubernetes, Kafka, Redis, WebSockets, multi-tenancy,
  purchase-order integration, Phase 8D/8E, LocalStack, Phase 9+, MLOps, LLM,
  RAG, or LangGraph work.
- Free-tier exhaustion leads to degraded/suspended portfolio availability and
  owner review, never automatic paid continuation.

Browser XSS is the principal new security risk. Mitigations are short-lived
access tokens, no offline access, session storage, strict CSP/security headers,
small dependency inventory, lockfile/advisory review, no token logging, and
backend authorization. These controls reduce but do not eliminate XSS risk and
do not establish production security approval.

## Acceptance criteria

Phase 8C implementation is complete only when all of the following are proven:

- [x] The repository owner has accepted this gate and Issue #77 scope.
- [ ] The static React/TypeScript/Vite SPA has no SSR, Pages Function, Worker,
      server session, browser secret, or OIDC client secret.
- [ ] Node/npm and every frontend dependency are pinned/reproducible and the
      exact justified dependency inventory is documented.
- [ ] The generated OpenAPI client matches canonical FastAPI and fails CI on
      drift.
- [ ] The page set implements the real product-to-audit workflow with accessible
      loading, empty, error, conflict, forbidden, waking, and unavailable states.
- [ ] The single list-reviews backend blocker works consistently in memory and
      PostgreSQL and reconstructs the pending queue after refresh.
- [ ] Authorization Code + PKCE S256 works with the exact public ZITADEL client,
      audience, scopes, callback, logout, and no offline access.
- [ ] One dedicated owner-controlled human portfolio operator has exactly the
      three application roles through a reviewed Terraform project grant and no
      administrator role or generated credential.
- [ ] Exact non-hierarchical roles shape UI convenience while FastAPI remains
      the only authorization authority.
- [ ] CORS allows only exact reviewed origins, methods, and headers with no
      cookies/credentials or wildcard.
- [ ] Cloudflare Pages is exactly one Free static project from `main`, has no
      preview/live-API wildcard or paid runtime, and serves reviewed headers.
- [ ] Supported Cloudflare/ZITADEL changes have reviewed HCP Terraform state and
      plans; owner/manual exceptions and authority do not overlap.
- [ ] Frontend, OpenAPI, browser, Terraform, repository, Python, PostgreSQL,
      container, CORS, and full regression checks pass.
- [ ] Live evidence proves browser login, exact role outcomes, Render calls,
      Neon persistence, recommendation decision/audit, reload, logout, wake,
      request correlation, deployment revision, and rollback identity.
- [ ] No reusable credential, private/customer data, paid resource, unrelated
      capability, or false production/AWS/AI claim is introduced.
- [ ] A Phase 8C review records exact evidence, security/cost/operational limits,
      residual risk, and an explicit owner decision.

Implementation delivery does not itself complete Phase 8 or authorize Phase 8D
or Phase 8E. Phase 8 remains Current until its later gates and accepted review
are complete.

## Manual and owner-controlled boundaries

The owner must separately authorize and, where required, perform:

- separate authorization for Batch 2, Batch 3, and each live-provider step;
- Cloudflare account/email/MFA/CAPTCHA/payment-state verification;
- repository-only Cloudflare GitHub App connection;
- HCP Cloudflare workspace creation, public account ID, sensitive scoped token,
  reviewed plan, and apply;
- exact Pages URL capture;
- HCP ZITADEL production callback/logout/origin plan and apply;
- owner-controlled human portfolio-operator creation/authentication and the
  reviewed Terraform grant of exactly the three application roles;
- Render exact CORS value and protected backend release approval;
- Cloudflare production deployment review/rollback selection;
- interactive ZITADEL user login/MFA and live authenticated smoke; and
- Phase 8C review acceptance.

No credential, MFA code, token, API secret, access token, or private response is
to be pasted into chat or committed. If a platform requires payment, a broader
token, an unsupported provider action, or a security weakening, stop before
mutation and return to the owner.

## Current official-source evidence

This proposal rechecked the following primary sources on 2026-08-13:

- [Cloudflare Pages build configuration](https://developers.cloudflare.com/pages/configuration/build-configuration/)
- [Cloudflare Pages Git integration](https://developers.cloudflare.com/pages/configuration/git-integration/)
- [Cloudflare Pages limits](https://developers.cloudflare.com/pages/platform/limits/)
- [Cloudflare Pages branch controls](https://developers.cloudflare.com/pages/configuration/branch-build-controls/)
- [Cloudflare Pages SPA serving](https://developers.cloudflare.com/pages/configuration/serving-pages/)
- [Cloudflare Pages headers](https://developers.cloudflare.com/pages/configuration/headers/)
- [Cloudflare Pages API](https://developers.cloudflare.com/api/resources/pages/)
- [Official Cloudflare Pages Terraform resource](https://registry.terraform.io/providers/cloudflare/cloudflare/latest/docs/resources/pages_project)
- [ZITADEL recommended OAuth/OIDC flows](https://zitadel.com/docs/guides/integrate/login/oidc/oauth-recommended-flows)
- [ZITADEL OIDC login guide](https://zitadel.com/docs/guides/integrate/login/oidc/login-users)
- [ZITADEL application and development-mode guidance](https://zitadel.com/docs/guides/manage/console/applications-overview)
- [ZITADEL role/audience scopes](https://zitadel.com/docs/guides/integrate/retrieve-user-roles)
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [Vite public environment variables](https://vite.dev/guide/env-and-mode)
- [Node.js release status](https://nodejs.org/en/about/previous-releases)
- [`oidc-client-ts`](https://authts.github.io/oidc-client-ts/)
- [Playwright best practices](https://playwright.dev/docs/best-practices)

Free plans, provider schemas, security guidance, and versions can change.
Batch 3 must recheck them before any live mutation.

## Owner acceptance

The repository owner reviewed and accepted this gate on 2026-08-13. The
accepted statement is preserved verbatim:

> I accept the Phase 8C authenticated frontend and full-stack product gate under
> Issue #77, including the three implementation batches, the single required
> recommendation-list backend addition, the React/TypeScript/Vite static SPA,
> ZITADEL Authorization Code with PKCE S256, exact-origin CORS, Cloudflare Pages
> Free and HCP Terraform ownership boundaries, the documented owner-controlled
> actions, security/cost constraints, and residual limitations. I authorize
> Batch 1 implementation only. Later live Cloudflare, HCP, ZITADEL, Render, and
> deployment mutations remain separately authorized steps.

This acceptance authorizes the Phase 8C architecture and Batch 1 implementation
only after the gate acceptance merges to canonical `main`. It does not
authorize Batch 2 or Batch 3; Cloudflare account, project, or resource creation;
an HCP Cloudflare workspace or apply; a live ZITADEL mutation; a human operator
identity or grant mutation; a Render mutation or deployment; a backend
production CORS release; a secret or environment mutation; or a Phase 8C
completion claim. Phase 8 overall remains Current.
