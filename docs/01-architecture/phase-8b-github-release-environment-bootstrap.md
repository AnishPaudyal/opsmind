# Phase 8B GitHub protected release-environment bootstrap

## Purpose

This runbook defines the owner-controlled GitHub deployment environment used by
the Phase 8B protected migration, Render deployment, and authenticated smoke
workflow.

It is an operational companion to:

- `phase-8b-cloud-backend-gate.md`;
- `.github/workflows/cloud-release.yml`;
- `phase-8b-neon-bootstrap.md`; and
- `phase-8b-hcp-terraform-bootstrap.md`.

GitHub Actions owns release orchestration. The repository owner owns creation,
protection, configuration, approval, and secret handoff for the GitHub
deployment environment.

## Critical ordering rule

Create and protect the `phase-8b` environment manually **before the first
`cloud-release` workflow dispatch**.

Do not rely on a workflow run to create the environment implicitly.

The release workflow references:

`phase-8b`

and the environment must already have its reviewed protection rules before any
release job is allowed to reach that boundary.

Environment creation does not mean the release is ready to deploy. Secrets and
variables may remain unavailable until their producing bootstrap steps are
complete, and the protected deploy job must not be approved until the entire
required inventory is present.

## Environment contract

Create exactly one GitHub deployment environment named:

`phase-8b`

Configure it with the following contract.

| Setting | Required value |
| --- | --- |
| Environment name | `phase-8b` |
| Deployment branch policy | Selected branches and tags |
| Allowed branch | `main` only |
| Allowed tags | None |
| Required reviewer | Repository owner |
| Wait timer | None |
| Custom protection rules | None |
| Administrator bypass | Disabled if the repository plan/UI permits |
| Prevent self-review | Disabled while the initiating owner is the sole required reviewer |

Do not use an unrestricted deployment-branch policy.

Do not add pull-request refs, tags, feature branches, release branches, or
wildcards to the environment.

If a second independent trusted reviewer is intentionally added later, the
owner may separately review whether enabling prevent-self-review is desirable.
Do not enable it while the person triggering the controlled release is also the
only person able to approve it.

## Environment secrets

The `phase-8b` environment owns exactly these Phase 8B release secrets:

| Secret | Producer | Purpose |
| --- | --- | --- |
| `OPSMIND_MIGRATION_DATABASE_URL` | Neon | Direct TLS PostgreSQL URL used only by the protected Alembic migration |
| `RENDER_DEPLOY_HOOK_URL` | Render | Secret Render deploy hook invoked with the exact immutable image |
| `ZITADEL_SMOKE_PRIVATE_KEY` | ZITADEL owner key handoff | Private key used only to request the bounded read-only smoke token |

Do not store these values as repository-level secrets unless a separately
reviewed design explicitly changes the authority boundary.

Do not place any of them in:

- Git;
- workflow YAML;
- Terraform;
- HCP Terraform;
- Render Blueprint YAML;
- issues;
- pull requests;
- documentation;
- screenshots; or
- chat.

Environment approval protects access to these secrets, but it does not make
their values non-sensitive after they reach the runner.

## Environment variables

The `phase-8b` environment owns exactly these non-secret release variables:

| Variable | Producer | Purpose |
| --- | --- | --- |
| `RENDER_SERVICE_URL` | Render | Public HTTPS service URL used by health, readiness, and auth smoke |
| `ZITADEL_ISSUER` | ZITADEL | Exact trusted issuer used for token issuance and API validation |
| `ZITADEL_PROJECT_ID` | HCP Terraform output | Exact OpsMind project ID and API audience |
| `ZITADEL_SMOKE_USER_ID` | HCP Terraform output | Dedicated release-smoke service-account ID |
| `ZITADEL_SMOKE_KEY_ID` | ZITADEL smoke-key handoff | Key ID corresponding to the protected smoke private key |

These are environment variables, not GitHub secrets.

The values are deployment configuration and must still be reviewed for exact
identity. Do not treat "non-secret" as "untrusted" or permit arbitrary values.

## Explicit non-members

Do not add the following to the GitHub `phase-8b` environment:

- Neon pooled runtime URL;
- ZITADEL Terraform provider JWT Profile;
- HCP Terraform token;
- GitHub PAT;
- Render registry credential;
- SPA client secret;
- frontend configuration;
- Cloudflare credentials.

The Neon pooled runtime URL belongs only in Render as
`OPSMIND_DATABASE_URL`.

The ZITADEL Terraform provider JWT Profile belongs only in the sensitive HCP
Terraform workspace variable `zitadel_jwt_profile_json`.

The public SPA uses no client secret.

The selected HCP Terraform workflow uses its VCS integration and requires no
HCP API token in GitHub.

GHCR publication uses the ephemeral repository `GITHUB_TOKEN`; no PAT is part
of the Phase 8B secret inventory.

## First-creation procedure

Before dispatching `cloud-release` for the first time:

1. open the repository Settings;
2. open Environments;
3. create `phase-8b`;
4. configure deployment branches as selected branches and permit only `main`;
5. add the repository owner as the required reviewer;
6. leave prevent-self-review disabled while that owner is the sole reviewer;
7. disable administrator bypass if the available repository plan/UI permits;
8. configure no wait timer and no custom deployment protection rule;
9. verify the environment exists before any release dispatch.

Do not approve a protected deploy merely because the environment exists.

## First-release bootstrap behavior

The initial controlled publication intentionally has a split lifecycle.

The reviewed implementation is merged to `main` first.

The owner may then dispatch `cloud-release`.

The publication job may:

- verify all required checks for the exact `main` SHA;
- build the image once;
- scan it;
- publish the full-SHA image to GHCR; and
- resolve the immutable manifest digest.

The deploy job references `phase-8b` and must remain behind its owner approval
boundary.

After the first publication creates the GHCR package:

- make the package public;
- verify it remains associated with this repository;
- capture the real immutable digest;
- do not create a `latest` release authority.

The first valid `render.yaml` is then added through the separately reviewed
follow-up change using that actual immutable digest.

After Render Blueprint bootstrap, Neon bootstrap, ZITADEL/HCP bootstrap, and
all secret handoffs are complete, the owner may approve a still-valid pending
protected deploy or deliberately rerun the controlled release if necessary.

Never approve a deploy job merely to discover which configuration is missing.

## Approval checklist

Before approving `Migrate, deploy, and smoke`, verify:

- the workflow SHA is the intended reviewed `main` SHA;
- required repository checks are green;
- the published GHCR package is public;
- the exact immutable image digest is retained;
- the reviewed Render service exists;
- `RENDER_SERVICE_URL` is populated;
- `ZITADEL_ISSUER` is populated;
- `ZITADEL_PROJECT_ID` is populated;
- `ZITADEL_SMOKE_USER_ID` is populated;
- `ZITADEL_SMOKE_KEY_ID` is populated;
- `OPSMIND_MIGRATION_DATABASE_URL` is populated;
- `RENDER_DEPLOY_HOOK_URL` is populated;
- `ZITADEL_SMOKE_PRIVATE_KEY` is populated;
- Render has the pooled runtime `OPSMIND_DATABASE_URL`;
- every provider dashboard still shows the reviewed zero-cost plan/resource
  shape;
- no payment, paid resource, automatic upgrade, or unexpected authority is
  required.

If any item is missing or unexpected, reject or leave the deployment waiting.
Do not approve the job to bypass the gate.

## Secret rotation

For an environment secret rotation:

1. generate the replacement at its authoritative provider;
2. replace the GitHub environment secret;
3. run the bounded validation for that credential;
4. revoke the previous provider credential only after replacement validation.

Do not retain old private keys or deploy hooks merely for convenience.

Changing a non-secret environment variable still requires identity review. In
particular, issuer, project ID, service URL, smoke user ID, and key ID changes
must not silently redirect release authority to another provider resource.

## Completion evidence

GitHub protected-environment bootstrap is evidenced only when:

- `phase-8b` exists before release dispatch;
- only `main` may deploy through it;
- the reviewed owner approval boundary is configured;
- administrator bypass is disabled if supported;
- the exact three secrets are stored at the environment level;
- the exact five variables are stored at the environment level;
- no PAT or unrelated credential is introduced;
- the first protected deployment remains gated until all upstream bootstrap
  prerequisites are satisfied.

Until these conditions are observed, this document defines the GitHub
environment procedure and does not claim that the live release environment has
been configured.
