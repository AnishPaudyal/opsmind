# OpsMind Cloudflare Pages Terraform

This directory defines the credential-free, provider-supported configuration
for one OpsMind static Cloudflare Pages project. It is governed by the
[accepted Phase 8C gate](../../docs/01-architecture/phase-8c-authenticated-frontend-gate.md)
and accepted ADR-0007.

## Ownership

Terraform through a separate HCP Terraform workspace is authorized to own
exactly:

- one `cloudflare_pages_project`;
- its `AnishPaudyal/opsmind` Git source;
- production branch `main`;
- the `frontend` root, `npm run build` command, and `dist` output;
- permanently disabled automatic production deployments;
- disabled preview deployments;
- equal explicit production and preview `fail_open` values required by the
  Cloudflare API; and
- the five public OpsMind frontend build values.

It intentionally does not own Cloudflare account creation, the GitHub App
connection, tokens, domains, DNS, Access, Workers, Pages Functions, KV, D1, R2,
other storage, or another Pages project. It also does not own ZITADEL, Render,
Neon, GHCR, GitHub environments, migrations, or releases.

## Inputs and credentials

The HCP workspace supplies three Terraform variables:

| Variable | Sensitive | Purpose |
| --- | --- | --- |
| `cloudflare_account_id` | No | Public account identifier; never commit the owner's value |
| `cloudflare_api_token` | Yes | Write-only token with only Pages Write access |
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

The owner completed that connection with access restricted to
`AnishPaudyal/opsmind`; Terraform must not manage or broaden it.

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

The verified resource was created with production automatic deployment disabled
and preview deployment set to `none`. Its production and preview deployment
configurations both set `fail_open = true` to satisfy the Cloudflare API; these
values do not enable either deployment path. The provider-issued origin is
`https://opsmind-app.pages.dev`; it was captured from applied state rather than
guessed.

Substep 7 temporarily enabled `production_deployments_enabled` so the first
canonical production deployment could be completed. PR #91 then demonstrated
that a later merge to `main` could also deploy automatically. That deployment
was harmless, but the delivery path did not preserve an explicit production
authorization boundary. The owner therefore disabled automatic production
deployments through Cloudflare Branch control. This source now records the
steady-state value `false`, matching live containment.

Because the manual containment already changed the provider, the expected HCP
run after this source reaches `main` is zero additions, changes, and destroys.
External-drift or refresh messaging that records the earlier manual change is
acceptable. Any plan proposing `false` to `true`, a project replacement, or an
unrelated change is not acceptable.

GitHub remains connected to `AnishPaudyal/opsmind`, but repository pushes and
merges are not production-release authorization. Future production releases
use the separately protected, manually dispatched workflow described in the
[frontend release-control runbook](../../docs/01-architecture/phase-8c-frontend-release-control.md).
That workflow is not operational until its GitHub environment and credential
boundary are separately reviewed and provisioned.

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

Automatic production deployments must not be re-enabled for rollback. A future
owner-authorized rollback rebuilds and redeploys a known-good commit SHA through
the same protected manual workflow when policy permits. It is not a Terraform
destroy. Destroying the Pages project also destroys its provider hostname and
deployment history and therefore requires explicit owner review. Terraform
destruction does not imply any ZITADEL, Render, or Neon rollback.
