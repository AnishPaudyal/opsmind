# Phase 8C HCP Terraform Cloudflare bootstrap and delivery contract

## Purpose and current boundary

This runbook defines the owner-controlled HCP Terraform workspace for
the Cloudflare Pages configuration in `infra/cloudflare`. It is an operational
companion to the [accepted Phase 8C gate](phase-8c-authenticated-frontend-gate.md),
accepted ADR-0007, and the
[Cloudflare Terraform README](../../infra/cloudflare/README.md).

Phase 8C Batch 3 Substep 1 prepared this credential-free repository contract.
Substep 2 completed the separately authorized Cloudflare/GitHub/HCP bootstrap
and credentialed plan. Substep 3 is Complete: after the first apply failed
safely before project creation, the corrected apply created exactly one dormant
Pages project, captured its provider-issued origin, and a later plan verified no
drift. No Pages deployment exists. The repository owner has since authorized
Substep 4 only as the exact-origin source packet; Substeps 5–8 and all provider
mutation remain unauthorized.

## Verified bootstrap and apply evidence

The owner verified Cloudflare Free at `$0` and restricted its GitHub App to
`AnishPaudyal/opsmind`. The API token has Pages Write only and exists only as a
Sensitive/write-only HCP variable. Workspace `opsmind-phase-8c-cloudflare`
uses Terraform `1.15.8`, Remote execution, `infra/cloudflare` as its working
directory, `infra/cloudflare/**` as its VCS trigger, and disabled auto-apply.

Credentialed speculative plan `run-APcJQx868crLvfka` completed with one add,
zero changes, and zero destroys; as a plan-only run it created no resource.
Applyable plan `run-i4t9u2G97QgeNP4k` had the same summary. The owner confirmed
the reviewed apply, but Cloudflare rejected its create request with error
`8000066`: production and preview `fail_open` must be equal. The failure
occurred on pre-correction commit
`81b5ebd490770d89a89019571e096e050b5733bf` before successful Pages project
creation.

PR #84, `fix: align Cloudflare Pages fail-open configuration`, then merged as
`3c150149c18edf3af780966bff95b07ecede3840`. Its final reviewed history
contained the initial `5b4f510` Cloudflare correction, focused `00875d4`
Debian `util-linux` security remediation required by the container gate, and
`7b36352` container-security validation documentation. The final PR changed ten
files, including `Dockerfile`; only the initial Cloudflare correction was
container-neutral.

Corrected standard run `run-yV7o6SRhU4MH4UVB` used branch `main`, canonical
commit `3c150149c18edf3af780966bff95b07ecede3840`, and Terraform `1.15.8`.
Its explicitly confirmed plan and apply each contained exactly one add, zero
changes, zero destroys, and zero invoked actions. State version
`sv-TQj2vumd74SpzaVx` contains only `cloudflare_pages_project.opsmind` and
reports:

- project name `opsmind-app` and provider origin
  `https://opsmind-app.pages.dev`;
- production branch `main` and GitHub source `AnishPaudyal/opsmind`;
- root `frontend`, build `npm run build`, and output `dist`;
- equal preview and production `fail_open = true`;
- preview deployment setting `none`, production automatic deployment disabled,
  and PR comments disabled; and
- the five existing public production `VITE_OPSMIND_*` values populated.

The project is dormant: `canonical_deployment` and `latest_deployment` are both
`null`. The computed `source.config.deployments_enabled = true` field is not
evidence of a deployment; the controlling preview and production settings above
remain disabled. Later manual run `run-hTpLxJ4MaKh3sxjK`, also on canonical
`main` at `3c150149c18edf3af780966bff95b07ecede3840` with Terraform `1.15.8`,
reported zero adds, changes, destroys, and invoked actions: the live resource
matches the reviewed configuration. Substep 3 is Complete.

## Authority boundary

HCP Terraform will own:

- remote state for `infra/cloudflare`;
- serialized credentialed runs and history;
- one reviewed Cloudflare Pages project plan; and
- separately owner-approved applies.

GitHub Actions owns only credential-free formatting, locked backendless
initialization, provider verification, and validation.

The repository owner owns:

- Cloudflare Free account, email, MFA, recovery, and payment-state checks;
- the Cloudflare GitHub App connection;
- HCP workspace bootstrap and VCS settings;
- the Cloudflare account ID and scoped API token;
- selection and availability verification of the public Pages project name;
- review and approval of every apply; and
- capture of the provider-issued stable Pages origin.

Terraform must not manage the Cloudflare account, GitHub App installation, HCP
organization/project/workspace, credential bootstrap, ZITADEL, Render, Neon,
GHCR, GitHub environments, database migrations, or releases.

## Zero-cost and security preconditions

Stop before mutation unless all of the following remain true:

1. Cloudflare offers the account and one static Pages project on Free without a
   payment method, trial conversion, recurring charge, or automatic upgrade.
2. The GitHub integration can be limited to `AnishPaudyal/opsmind` rather than
   unnecessarily broad repository access.
3. The provider token can be limited to Pages Write for the owner-controlled
   account.
4. HCP Terraform Remote execution, VCS integration, state, and reviewed manual
   apply remain within its approved free boundary.
5. The plan contains exactly one `cloudflare_pages_project` and no other
   resource.
6. Production automatic deployment and previews are disabled in the initial
   plan.
7. No credential needs to enter Git, GitHub Actions, frontend configuration,
   documentation, screenshots, terminal output, or chat.

Stop for owner review if any paid feature, broader token, unexpected resource,
change, destroy, replacement, secret exposure, or overlapping manual/Terraform
ownership appears.

## Required Cloudflare-to-GitHub connection

The official provider requires Cloudflare to have a supported GitHub
connection before it can create a Pages project with a `source` configuration.
The owner performs this once through Cloudflare and GitHub:

1. authenticate to the Cloudflare Free account;
2. choose the supported GitHub integration;
3. authorize only `AnishPaudyal/opsmind` when repository scoping is available;
4. reject requests for unrelated repository or organization access; and
5. verify no personal access token was created or copied into the repository.

Terraform does not automate this bootstrap exception. Do not create the Pages
project manually; after the connection exists, the reviewed HCP apply remains
the Pages-project creation authority.

## Workspace contract

Create exactly one VCS-driven workspace only after separate authorization:

| Setting | Required value |
| --- | --- |
| Workspace name | `opsmind-phase-8c-cloudflare` |
| Execution mode | Remote |
| Terraform version | `1.15.8` exactly |
| VCS repository | `AnishPaudyal/opsmind` only |
| VCS branch | `main` |
| Working directory | `infra/cloudflare` |
| VCS path filter | `infra/cloudflare/**` |
| Apply method | Manual apply |
| Auto apply | Disabled |
| Automatic speculative PR plans | Disabled |
| Run triggers | None |
| HCP Terraform agents | None |
| Run tasks | None |
| SSH key | None |
| Remote-state sharing | None |

Do not add a `cloud` block or backend configuration to source. Do not create an
HCP API token for GitHub Actions.

## Workspace variables

Create exactly these Terraform variables at the later owner boundary:

| Key | Sensitive | HCL | Source |
| --- | --- | --- | --- |
| `cloudflare_account_id` | No | No | Public ID shown by the owner-controlled Cloudflare account |
| `cloudflare_api_token` | Yes | No | Owner-created token with only Pages Write access |
| `pages_project_name` | No | No | Owner-selected available public Pages project name |

Enable HCP's Sensitive/write-only setting before saving
`cloudflare_api_token`. Never put its value in a description. Do not create
workspace variables for the five public `VITE_OPSMIND_*` values; the reviewed
Terraform resource already declares those values as plain build configuration.

No ZITADEL credential, Neon URL, Render secret, GitHub environment secret, or
human authentication credential belongs in this workspace.

## First plan review

After canonical source and the HCP configuration version match, start one
standard plan and leave it pending explicit owner apply approval. Expected
summary:

```text
Plan: 1 to add, 0 to change, 0 to destroy
```

Expected inventory:

```text
cloudflare_pages_project.opsmind
```

Verify the plan shows:

- GitHub source `AnishPaudyal/opsmind` and production branch `main`;
- root `frontend`, build `npm run build`, and output `dist`;
- production automatic deployment disabled;
- preview deployment setting `none` and PR comments disabled;
- equal explicit `preview.fail_open = true` and `production.fail_open = true`;
- exactly five plain public `VITE_OPSMIND_*` values;
- no secret build value;
- no Function, Worker, KV, D1, R2, Access, domain, DNS, analytics, or other
  Cloudflare resource; and
- no paid setting, change, destroy, or replacement.

Reject the plan rather than broadening access or editing live configuration if
any item differs.

## First apply and stable-origin handoff

After separate owner approval, apply the already-reviewed saved plan once. A
successful result should be exactly one resource added. Independently verify
the project remains Free, production automatic deployment is disabled, preview
deployments are disabled, no deployment was queued, and no extra resource
exists.

Capture only the non-secret `pages_project_name` and `pages_origin` outputs.
The origin must be the actual provider-issued HTTPS value; do not reconstruct
or guess it. The Substep 4 repository packet uses that exact origin for:

- ZITADEL callback, post-logout, and allowed-origin configuration with
  `dev_mode = false`;
- Render `OPSMIND_CORS_ALLOWED_ORIGINS` as a JSON array containing only that
  origin.

The owner-created human operator and its exact three-role Terraform grant begin
Substep 5 and are intentionally absent from the Substep 4 repository packet.

The future Render value has this shape only after replacing the marker with
the verified provider output:

```text
OPSMIND_CORS_ALLOWED_ORIGINS=["https://opsmind-app.pages.dev"]
```

None of those changes belongs in the dormant-project bootstrap.

Committing the source does not apply ZITADEL or synchronize Render. Because the
VCS-driven ZITADEL workspace watches `infra/zitadel/**`, merge of the Substep 4
PR may queue a credentialed plan and therefore remains an explicit owner gate.

## Substep 5 ZITADEL operator-grant handoff

PR #86 merged the exact-origin source as
`18d29c92dd0070faad8038c88d159d533ad353e8`. HCP ZITADEL run
`run-UXDXd9rKDhe74ocK` used that canonical configuration and verified zero
additions, one in-place `zitadel_application_oidc.spa` change, zero destroys,
and zero replacements. It remains deliberately unapplied at Pending
confirmation.

Substep 5 repository source adds one required nonsensitive
`portfolio_operator_user_id` input and one
`zitadel_user_grant.portfolio_operator`. The owner must first create or select
one dedicated, MFA-protected, non-administrator human in the existing OpsMind
organization outside Terraform. Prefer a new dedicated identity; do not reuse
the organization owner as the permanent product operator. Confirm that it has
no IAM, organization, project-owner, or other administrative role and copy only
its public numeric ZITADEL user ID. Never place password/passkey, MFA, recovery,
session, token, private-key, or personal account material in HCP Terraform, Git,
CI, logs, screenshots, or chat.

After the operator-grant PR merges, the owner supplies only that public ID as a
fourth nonsensitive Terraform workspace variable with HCL disabled. Verify the
next run's exact configuration SHA and variable inventory before planning.
Under separate authorization, discard the older origin-only run and allow
exactly one new standard plan. With the origin change still unapplied and no
drift, the only acceptable result is:

```text
Plan: 1 to add, 1 to change, 0 to destroy
Replacement: 0
Add: zitadel_user_grant.portfolio_operator
Change: zitadel_application_oidc.spa (in place)
```

The grant uses the existing organization and `zitadel_project.opsmind.id`, and
contains exactly `opsmind.business.read`, `opsmind.business.write`, and
`opsmind.recommendation.decide`. Stop for any different count; any destroy or
replacement; any project, application, client-ID, role-definition,
release-smoke, or bootstrap-identity/key change; any Terraform-managed user;
any administrator role; any `zitadel_project_grant` or `project_grant_id`; or
any unrelated drift. Plan review and apply remain separate owner checkpoints.

## Later delivery sequence

Each step remains separately authorized:

1. merge this credential-free foundation;
2. perform the owner Cloudflare/GitHub/HCP bootstrap;
3. apply the one-resource dormant Pages project;
4. capture its provider-issued exact origin and verify no deployment started;
5. merge the exact-origin ZITADEL/Render/Cloudflare wiring;
6. create the human operator and apply the reviewed ZITADEL update and grant;
7. synchronize the Render Blueprint and run the existing protected backend
   release;
8. enable and verify the Pages production deployment from canonical `main`;
9. perform live authenticated browser acceptance; and
10. prepare the Phase 8C review for explicit owner acceptance.

No wildcard CORS, wildcard preview origin, broad redirect, temporary client
secret, or insecure production bypass is permitted.

## Rollback boundaries

- Frontend rollback selects a prior successful Cloudflare Pages production
  deployment; do not destroy the project merely to roll back assets.
- Backend rollback selects a retained immutable Render/GHCR image through the
  existing protected release authority.
- Operator access rollback removes the exact ZITADEL project grant; human
  credential recovery remains owner-controlled.
- CORS rollback restores a previously reviewed exact-origin configuration; it
  never introduces `*`.
- ZITADEL callback rollback uses an exact previously reviewed HTTPS origin.
- No frontend rollback implies destructive Neon schema or data rollback.

These rollback paths are documented designs, not exercised evidence. Phase 8C
cannot be marked Complete until live delivery, rollback identity, security,
cost, persistence, and owner-accepted review evidence exist.
