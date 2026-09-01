# Phase 8C Protected Frontend Release Control

## Status and authority

- Status: Prepared, not operational
- Governing issue: [#77](https://github.com/AnishPaudyal/opsmind/issues/77)
- Governing architecture: [ADR-0007](decisions/0007-select-phase-8-zero-cost-cloud-deployment-and-product-delivery-architecture.md)
- Cloudflare project: `opsmind-app`
- Canonical URL: `https://opsmind-app.pages.dev`
- Release workflow: `.github/workflows/frontend-release.yml`

This runbook records the repository-controlled production frontend release
boundary. It does not authorize creation of the GitHub environment, provider
credentials, or a workflow dispatch. The workflow must not run until the
repository owner separately reviews and provisions that control plane.

## Steady-state delivery model

Cloudflare retains its repository-scoped GitHub connection to
`AnishPaudyal/opsmind`, production branch `main`, `frontend` build root,
`npm run build` command, and `dist` output. Terraform permanently sets
`production_deployments_enabled = false`; preview deployments and PR comments
also remain disabled. A push or merge is therefore source delivery, not
production-release authorization.

Production release uses only the manually dispatched `Frontend release`
workflow. Its required `git_sha` input must be one lowercase 40-character Git
SHA. The build job:

1. requires the workflow itself to be dispatched from `main`;
2. checks out exactly the supplied SHA with complete history;
3. proves `HEAD` equals that SHA and that the commit is reachable from current
   canonical `origin/main`;
4. installs only the locked frontend graph;
5. runs formatting, lint, strict TypeScript, coverage tests, deterministic
   OpenAPI drift validation, the production build, dependency audit, and the
   protected browser suite; and
6. transfers only the validated `frontend/dist` artifact to the deployment
   job.

No branch, `HEAD`, mutable tag, or `latest` fallback exists.

## Protected GitHub environment

Before the first dispatch, the repository owner must separately create and
review the environment named:

```text
phase-8c-frontend
```

Its required control contract is:

- owner-required reviewer protection;
- administrator bypass disabled where the GitHub plan supports it;
- deployment limited to the intended `main`/workflow policy;
- no unreviewed custom protection rule; and
- no value provisioned until its authority and source have been verified.

The deployment job, not the credential-free build job, references this
environment. GitHub therefore completes the exact-SHA build and validation
before requesting production approval. The environment must avoid a reviewer
configuration that deadlocks its sole initiating owner; the owner must review
the final GitHub-supported self-review behavior during provisioning.

## Credential boundary

The protected environment supplies exactly:

| Kind | Name | Purpose |
| --- | --- | --- |
| Secret | `CLOUDFLARE_API_TOKEN` | Authenticate the bounded Pages deployment |
| Variable | `CLOUDFLARE_ACCOUNT_ID` | Select and attest the intended account |

Neither value exists in repository source. The future token must be restricted
to the OpsMind Cloudflare account and only the Pages write/edit permission
needed for deployment. It must not grant DNS, account administration, Workers,
billing, unrelated resource, or Global API Key authority.

## Provider and deployment guards

The deployment job uses exact Wrangler `4.127.1` through a workflow-scoped npm
invocation; Wrangler is not added to the frontend runtime dependency graph.
Before deployment, the job:

- validates the account credential against `CLOUDFLARE_ACCOUNT_ID`;
- lists Pages projects through the selected account;
- requires exactly one match named `opsmind-app` whose production branch is
  `main`;
- verifies the artifact contains `index.html` and `_headers`; and
- rejects a `_worker.js` or Functions directory.

Wrangler `4.127.1` does not expose experimental provisioning/auto-create flags
on `pages deploy`. The workflow therefore performs the explicit existing-
project guard and runs deployment with standard input closed; a missing project
must fail rather than accept an interactive creation path.

The production command is equivalent to:

```text
wrangler pages deploy frontend/dist \
  --project-name opsmind-app \
  --branch main \
  --commit-hash <authorized-40-character-SHA> \
  --commit-message "Protected frontend release <authorized-SHA>" \
  --commit-dirty=false
```

One non-cancelling concurrency group prevents overlapping production frontend
releases.

## Release evidence and verification

The workflow inventories production deployments immediately before and after
upload, then requires exactly one new production deployment whose Cloudflare
metadata contains the authorized SHA and branch `main`. It records only safe
release evidence:

- requested and checked-out SHA;
- Pages deployment ID and deployment-specific URL;
- canonical URL and production environment;
- Cloudflare-attached commit SHA; and
- current backend revision.

The post-deployment gate verifies the canonical root, built static assets,
`/auth/callback` SPA shell, security headers, backend `/health`, backend
`/ready`, PostgreSQL readiness, revision metadata, and exact production-origin
CORS. Any identity, deployment, or smoke discrepancy fails visibly.

## Rollback and provider reconciliation

A rollback must remain explicit and protected. When separately authorized, the
owner may dispatch the same workflow with a known-good commit that remains
reachable from canonical `main`. Automatic production deployments must not be
temporarily re-enabled to perform rollback.

The live containment change set automatic production deployment to `false`
before this repository reconciliation. After this source merges, the HCP
Cloudflare workspace should refresh to desired `false` and live `false`, with
an expected plan of zero additions, changes, and destroys. External-drift
messaging about the prior manual containment is acceptable; any proposal to
re-enable production automation, replace the project, or change another
provider property is a stop condition.

## Current limitation

This release mechanism is prepared but not operational. The
`phase-8c-frontend` environment, reviewer protection, API token, account
variable, first dispatch, and acceptance evidence all require separate owner
authorization. No repository merge alone constitutes a frontend release.
