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

Committing this source did not itself change live ZITADEL state. The later
reviewed HCP apply updated the production SPA and created the dedicated human
operator's exact three-role grant. Local frontend tests use deterministic
fixtures rather than weakening the live client with localhost production
values.

The SPA uses JWT access tokens and requests the reviewed project-role scope.
ZITADEL must assert the granted application roles in that access token so the
backend can consume the project-ID-qualified roles claim. ID-token role
assertion remains disabled because an ID token is not API authorization.

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

HCP run `run-UXDXd9rKDhe74ocK` verified only the production-origin proposal as
zero additions, one in-place change, and zero destroys. It was never applied
and was deliberately discarded. The owner supplied public operator ID
`387560808021797348` as the fourth nonsensitive HCP variable. Combined run
`run-FU4enYWrPWDffWTe` applied one
`zitadel_user_grant.portfolio_operator` addition and one in-place
`zitadel_application_oidc.spa` change with zero destroys or actions, producing
state version `sv-G1nWZwhMs8e5o9iV`. Immediate run
`run-uMRmTGN2RoDUBRJa` verified zero additions, changes, destroys,
replacements, or actions. Substep 5 is technically Complete.
