# OpsMind frontend foundation

This directory contains the Phase 8C Batch 1 static React/TypeScript/Vite
application foundation. It establishes browser routing, session-only ZITADEL
Authorization Code with PKCE, a generated FastAPI contract, typed HTTP
transport, bounded query behavior, accessible reusable states, and a responsive
workspace shell.

It does not yet implement the operational product-to-audit workflow, the
recommendation-list backend endpoint, backend CORS, production identity
redirects, a human operator grant, Cloudflare delivery, or any live deployment.
Those remain separately gated Batch 2 and Batch 3 work.

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
are intentionally not configured in Batch 1.

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
