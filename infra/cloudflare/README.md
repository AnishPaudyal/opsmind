# OpsMind Cloudflare Pages Terraform

This directory defines the credential-free, provider-supported foundation for
one future OpsMind static Cloudflare Pages project. It is governed by the
[accepted Phase 8C gate](../../docs/01-architecture/phase-8c-authenticated-frontend-gate.md)
and accepted ADR-0007.

## Ownership

Terraform through a separate HCP Terraform workspace will own exactly:

- one `cloudflare_pages_project`;
- its `AnishPaudyal/opsmind` Git source;
- production branch `main`;
- the `frontend` root, `npm run build` command, and `dist` output;
- disabled production automation during the origin-capture bootstrap;
- disabled preview deployments; and
- the five public OpsMind frontend build values.

It intentionally does not own Cloudflare account creation, the GitHub App
connection, tokens, domains, DNS, Access, Workers, Pages Functions, KV, D1, R2,
other storage, or another Pages project. It also does not own ZITADEL, Render,
Neon, GHCR, GitHub environments, migrations, or releases.

## Inputs and credentials

The future HCP workspace supplies three Terraform variables:

| Variable | Sensitive | Purpose |
| --- | --- | --- |
| `cloudflare_account_id` | No | Public account identifier; never commit the owner's value |
| `cloudflare_api_token` | Yes | Write-only token with only provider-supported Pages Read/Write access |
| `pages_project_name` | No | Owner-selected available public name, validated before the first run |

Do not create a committed `.tfvars` file. Never place the token, account ID, or
any provider credential in source, documentation, workflow configuration,
terminal output, screenshots, or chat.

The five `VITE_OPSMIND_*` values in `main.tf` are deliberately public and are
compiled into the static browser bundle. No secret, database URL, private key,
deploy hook, or client secret may use a `VITE_` name.

## GitHub integration prerequisite

Cloudflare requires its supported GitHub integration before a Pages project
with a Git source can be created. The repository owner must establish that
connection manually and scope it only to this OpsMind repository when the UI
permits repository selection. A GitHub personal access token is neither
required nor accepted by this configuration.

Do not perform that owner action until its later live-bootstrap substep is
separately authorized.

## SPA routing and static headers

Cloudflare Pages documents native single-page-application fallback when the
published site has no top-level `404.html`: unknown paths are served the root
application so the existing React `BrowserRouter` can resolve them. The
frontend intentionally has no `404.html` and this foundation does not add a
habitual `_redirects` rewrite. The later deployed acceptance must still prove
direct navigation and refresh on protected deep links.

Cloudflare copies `frontend/public/_headers` into the Vite output. Its policy
allows same-origin static assets, the exact Render API connection, and the
exact ZITADEL issuer needed by the current Authorization Code with PKCE flow.
The built output contains external script and stylesheet assets, so no
`unsafe-inline`, `unsafe-eval`, or wildcard source is required.

## Expected first plan and apply

The first credentialed HCP plan is expected to be exactly:

```text
Plan: 1 to add, 0 to change, 0 to destroy
```

The only address is:

```text
cloudflare_pages_project.opsmind
```

The resource starts with production automatic deployment disabled and preview
deployment set to `none`. A successful apply therefore creates a dormant
project without deploying the frontend. Capture the provider-issued
`pages_origin` output only after apply; never guess a `pages.dev` hostname.

The verified origin is consumed by a later reviewed exact-origin change for
ZITADEL redirects, Render CORS, and final delivery. That later work is outside
this foundation.

Stop without applying if the plan contains another resource, any change or
destroy action, a paid feature, a Function or Worker, a domain or DNS change,
broader token requirements, or an automatically enabled deployment.

## Execution boundary

GitHub Actions performs only formatting, locked backendless initialization,
provider identity checks, and static validation. HCP Terraform owns remote
state, credentialed plans, and separately owner-approved applies.

Safe local checks are:

```bash
terraform fmt -check -recursive
terraform init -backend=false -input=false -lockfile=readonly
terraform validate
```

Do not run a credentialed local plan or apply against the live Cloudflare
account. Do not commit `.terraform`, state, plan files, credentials, or provider
cache content.

## Rollback and destruction

Later frontend delivery rollback selects a previously successful Cloudflare
Pages deployment; it is not a Terraform destroy. Destroying the Pages project
also destroys its provider hostname and deployment history and therefore
requires explicit owner review. Terraform destruction does not imply any
ZITADEL, Render, or Neon rollback.
