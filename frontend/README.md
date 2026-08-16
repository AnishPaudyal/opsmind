# OpsMind operational frontend

This directory contains the Phase 8C Batch 2 static React/TypeScript/Vite
operational workspace. It uses browser routing, session-only ZITADEL
Authorization Code with PKCE, a generated FastAPI contract, typed HTTP
transport, bounded query behavior, accessible reusable states, and a responsive
workspace shell to deliver the local product-to-audit workflow.

The workspace lists and creates products, manages inventory and demand,
calculates forecast/exposure/reorder evidence, persists actionable reviews,
reconstructs the review queue after refresh, and supports approval/rejection
with trusted audit history. It does not place external orders. Production
identity redirects, a human operator grant, Cloudflare delivery, and live
deployment remain separately gated Batch 3 work.

## Requirements

- Node.js `24.18.1` through the committed `.nvmrc`;
- npm `11.x` (the lock records `npm@11.16.0`);
- the repository's locked Python/uv environment for OpenAPI export.

With `nvm` installed:

```bash
nvm use
npm ci
```

Copy `.env.example` to an ignored `.env.local` and retain the five reviewed
public values. `VITE_*` values are embedded in the browser bundle and must never
contain a password, token, database URL, private key, client secret, deploy
hook, or provider credential.

The local example uses the loopback API and the existing public ZITADEL issuer,
project ID, and User Agent client ID. Production callback/logout/origin values
are intentionally not configured in Batch 2.

Run the backend at `http://127.0.0.1:8000` and configure its exact local browser
origin without enabling credentials:

```bash
export OPSMIND_CORS_ALLOWED_ORIGINS='["http://localhost:5173"]'
uv run uvicorn opsmind.main:app --reload --host 127.0.0.1 --port 8000
```

The local API may use the memory backend or the repository's disposable
PostgreSQL developer service. Deterministic automated tests use fake auth and
MSW; they never require live ZITADEL. The hosted SPA's localhost callback has
not been mutated or independently asserted during Batch 2, so optional manual
local ZITADEL sign-in may require separately authorized provider configuration.

## Feature map

- `/` uses only product and persisted-review collection reads for bounded
  operational totals.
- `/products` lists canonical products and exposes creation to users presenting
  `business:write`.
- `/products/:productId` composes inventory, demand, baseline forecast,
  stockout exposure, current reorder calculation, and review persistence.
- `/recommendations` reconstructs persisted reviews newest-first with exact
  product/status filters.
- `/recommendations/:recommendationId` shows immutable evidence, terminal
  decisions, and sequence-ordered trusted audit attribution.

Presentation roles improve usability only. FastAPI remains authoritative for
`business:read`, `business:write`, and `recommendation:decide`.

## Commands

```bash
npm run dev
npm run format:check
npm run lint
npm run typecheck
npm run test:coverage
npm run openapi:check
npm run build
npm run test:e2e
```

`npm run openapi:generate` deterministically exports FastAPI OpenAPI through
`scripts/export_openapi.py` and regenerates `src/api/generated/schema.ts` with
`openapi-typescript`. Commit both generated files when a reviewed backend
contract changes. `npm run openapi:check` generates into a temporary directory
and fails when either checked-in artifact is stale.

## Security and state boundaries

- `oidc-client-ts` owns state, nonce, and PKCE mechanics.
- OIDC transaction and user state use `sessionStorage`; `localStorage`, cookies,
  and query-cache token storage are not used.
- The browser requests only `openid`, `profile`, the exact project audience,
  and ZITADEL project-role scopes; it does not request `offline_access`.
- Presentation roles may improve navigation only. FastAPI remains the sole
  authorization authority.
- The API client uses `credentials: "omit"`, attaches Bearer and request-ID
  headers centrally, distinguishes `401` and `403`, and never logs tokens.
- Safe reads retry at most twice for unavailable/unexpected failures. Mutations
  never replay automatically.
