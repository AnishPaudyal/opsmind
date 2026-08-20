# OpsMind ZITADEL Terraform

This directory owns only the provider-supported ZITADEL resources authorized by
Phase 8B and the reviewed Phase 8C production-origin contract:

- the OpsMind project;
- the three exact application roles;
- the public User Agent / SPA OIDC application;
- the dedicated release-smoke machine identity; and
- its single `opsmind.business.read` grant; and
- one application-role grant for an owner-managed human portfolio operator.

It does not own:

- ZITADEL Cloud instance or bootstrap organization creation;
- the Terraform provider credential;
- any smoke private key;
- the human operator account, password/passkey, MFA, recovery, or session;
- Neon;
- Render;
- GitHub deployment environments;
- database migrations;
- release images; or
- frontend infrastructure.

## Credentials

`zitadel_jwt_profile_json` is supplied only as a sensitive HCP Terraform
workspace variable.

The release-smoke machine key is created separately by the repository owner
after Terraform creates the machine identity. Terraform must never generate,
store, or output that private key.

## Execution authority

Phase 8B uses HCP Terraform VCS-driven plans and reviewed applies. Do not run a
local `terraform apply` against the real ZITADEL instance.

The owner bootstrap and workspace settings are defined in
`docs/01-architecture/phase-8b-hcp-terraform-bootstrap.md`.

Local commands may be used for formatting, initialization without backend
configuration, provider locking, and static validation.

## Phase 8C production-origin boundary

The repository configures the SPA with only the captured Cloudflare Pages
production values:

- redirect URI `https://opsmind-app.pages.dev/auth/callback`;
- post-logout URI `https://opsmind-app.pages.dev/`;
- additional origin `https://opsmind-app.pages.dev`; and
- `dev_mode = false`.

Committing this source does not change live ZITADEL state. The HCP Terraform
plan and apply, owner-controlled human operator, and exact three-role operator
grant remain separately authorized later Phase 8C actions. Local frontend tests
use deterministic fixtures rather than weakening the live client with localhost
production values.

## Phase 8C portfolio-operator boundary

The required `portfolio_operator_user_id` input is the public numeric ZITADEL
ID of one dedicated, owner-managed human in the existing OpsMind organization.
It has no default and is intentionally nonsensitive because it is an identifier,
not a password, token, private key, session, or other credential. Supply it only
through the governed HCP Terraform workspace after the owner verifies that the
account is MFA-protected and has no `IAM_OWNER`, `ORG_OWNER`, `PROJECT_OWNER`,
or other administrative authority. Never place the person's email, credential,
MFA or recovery material, browser session, access token, or refresh token in
Terraform or Git.

Terraform manages only `zitadel_user_grant.portfolio_operator` for that existing
same-organization user. The grant references `zitadel_project.opsmind` and
contains exactly:

- `opsmind.business.read`;
- `opsmind.business.write`; and
- `opsmind.recommendation.decide`.

It does not create the human user or a cross-organization project grant. The
existing project, role definitions, public SPA client, `opsmind-release-smoke`
identity and read-only grant, and external `opsmind-terraform` bootstrap
identity remain unchanged.

HCP run `run-UXDXd9rKDhe74ocK` verified only the production-origin update as
zero additions, one in-place change, and zero destroys. It remains deliberately
unapplied at Pending confirmation. After this source is reviewed and merged,
the owner supplies only the public operator ID as a fourth nonsensitive HCP
Terraform variable, separately authorizes discarding that older run, and allows
exactly one new plan. With no drift, the combined plan must contain one added
`zitadel_user_grant.portfolio_operator`, one in-place change to
`zitadel_application_oidc.spa`, zero destroys, and zero replacements. Any other
resource or count is a stop condition, and apply requires separate approval.
