# Phase 8B ZITADEL bootstrap and key-handoff contract

## Purpose

This runbook defines the owner-controlled ZITADEL Cloud bootstrap required
before and after the Phase 8B HCP Terraform apply.

It is an operational companion to:

- `phase-8b-cloud-backend-gate.md`;
- `phase-8b-hcp-terraform-bootstrap.md`;
- `phase-8b-github-release-environment-bootstrap.md`;
- `infra/zitadel/`; and
- the protected cloud release workflow.

The bootstrap intentionally separates two credentials:

1. the ZITADEL Terraform provider credential; and
2. the release-smoke service-account credential.

They have different authorities, consumers, storage locations, and rotation
boundaries.

## Authority boundary

The repository owner manually owns:

- ZITADEL Cloud account and instance creation;
- administrator bootstrap;
- the dedicated OpsMind organization boundary;
- the Terraform bootstrap service account and its administrator assignment;
- the Terraform provider JWT Profile key;
- the release-smoke authentication key created after Terraform creates the
  smoke service account;
- private-key handoff and rotation.

Terraform owns only the reviewed provider-supported Phase 8B resources:

- one OpsMind project;
- the exact three OpsMind project roles;
- one public User Agent OIDC application;
- one release-smoke service account with no generated client secret; and
- one read-only role assignment for that smoke identity.

HCP Terraform owns:

- the sensitive Terraform-provider credential input;
- remote Terraform state;
- credentialed plans;
- reviewed applies; and
- non-secret Terraform outputs.

The protected GitHub `phase-8b` environment consumes only the release-smoke
credential and the non-secret ZITADEL deployment identities required by the
release workflow.

Terraform must not create or persist either private key.

## Cost and account boundary

Use one ZITADEL Cloud Free instance for Phase 8B.

Do not enable:

- Pro;
- Enterprise;
- a paid custom domain;
- additional paid instances;
- paid support;
- an automatic upgrade; or
- any other resource that introduces recurring cost.

If signup, administrator assignment, service-account creation, key creation, or
any other required Phase 8B action presents a payment requirement or upgrade
requirement, stop before accepting it and return to the Phase 8B cost gate.

Do not attach a payment method merely to bypass a Free-plan limitation.

## Instance and organization contract

Create or select one owner-controlled ZITADEL Cloud Free instance for OpsMind.

Use the generated ZITADEL Cloud domain. Phase 8B does not require a purchased
or custom domain.

Record only the non-secret generated hostname, for example:

`<instance>.zitadel.cloud`

The Terraform variable `zitadel_domain` receives the hostname only, without
`https://`, path, query, or fragment.

Use one dedicated organization named:

`OpsMind`

If the bootstrap process already created a suitable dedicated organization,
use that organization rather than creating a duplicate.

Capture its immutable organization ID for:

`zitadel_org_id`

Do not infer an organization ID from a name or URL.

The selected organization is the sole resource-owner boundary for the Phase 8B
Terraform-managed project, application, roles, smoke service account, and role
assignment.

## Issuer contract

The ZITADEL instance domain is also the OIDC issuer authority.

Verify the instance discovery document before handoff:

`https://<instance>.zitadel.cloud/.well-known/openid-configuration`

The returned issuer must match the reviewed ZITADEL instance.

The exact issuer becomes the protected GitHub environment variable:

`ZITADEL_ISSUER`

Do not use an issuer copied from another instance, organization, custom domain,
development environment, or documentation example.

## Terraform bootstrap service account

Within the dedicated `OpsMind` organization, manually create one service
account for Terraform bootstrap.

Use:

- username: `opsmind-terraform`;
- display name: `OpsMind Terraform Bootstrap`.

This service account exists only so the official ZITADEL Terraform provider can
manage the reviewed resources inside the dedicated OpsMind organization.

Assign the service account organization-level administrator authority:

`ORG_OWNER`

Do not assign:

`IAM_OWNER`

The provider credential must not have instance-wide administrator authority.

The organization boundary is deliberate: Terraform needs to manage the project,
application, project roles, service account, and role assignment inside
OpsMind, but it does not need to administer unrelated organizations or the
whole ZITADEL instance.

If the current ZITADEL Free plan or console requires a paid upgrade for this
administrator assignment, stop instead of widening or purchasing authority.

## Terraform provider JWT Profile key

Open the manually created `opsmind-terraform` service account and create a
private-key JWT credential through its key-management interface.

Use ZITADEL's generated/downloaded JWT Profile JSON for the Terraform provider.

The downloaded credential contains sensitive private-key material and is
one-time credential material.

Treat the entire JSON document as a secret.

It must never enter:

- Git;
- Terraform source;
- Terraform variables files;
- Terraform state;
- GitHub Actions;
- Render;
- issues;
- pull requests;
- documentation;
- screenshots;
- logs; or
- chat.

Do not create a PAT for Terraform.

Do not use a human-user credential for Terraform.

## HCP Terraform provider handoff

The provider credential is handed only to HCP Terraform.

Configure these exact Terraform-category workspace variables:

| Variable | Sensitive | HCL | Value |
| --- | --- | --- | --- |
| `zitadel_domain` | No | No | Generated ZITADEL Cloud hostname only |
| `zitadel_org_id` | No | No | Immutable dedicated OpsMind organization ID |
| `zitadel_jwt_profile_json` | Yes | No | Exact downloaded Terraform service-account JWT Profile JSON |

The provider credential must be stored only as:

`zitadel_jwt_profile_json`

in the HCP Terraform workspace.

Do not create an HCP API token for this handoff.

Once the sensitive variable has been entered and verified, remove any temporary
unencrypted local copy of the provider JWT Profile.

The provider key itself remains active because later reviewed Terraform plans
and applies require a provider credential.

Do not delete it immediately after the first apply.

## First HCP plan and apply

Follow `phase-8b-hcp-terraform-bootstrap.md` for the authoritative HCP workspace
and run procedure.

Before apply, the first empty-state plan is expected to propose the bounded
seven-resource Phase 8B ZITADEL set.

Do not approve a plan containing:

- instance resources;
- organization creation;
- administrator membership;
- private-key resources;
- unrelated users;
- unrelated applications;
- unrelated projects;
- unexpected replacements or destroys;
- Neon;
- Render;
- Cloudflare;
- GitHub;
- AWS; or
- paid infrastructure.

After review, the repository owner manually approves the HCP Terraform apply.

## Required Terraform outputs

After the reviewed apply succeeds, capture only the non-secret outputs needed
for later handoff:

- `project_id`;
- `spa_client_id`;
- `smoke_user_id`; and
- `smoke_role_keys`.

The project ID becomes:

`ZITADEL_PROJECT_ID`

in the protected GitHub `phase-8b` environment.

The smoke user ID becomes:

`ZITADEL_SMOKE_USER_ID`

in the same environment.

The smoke role output must contain only:

`opsmind.business.read`

Do not treat `spa_client_id` as a secret. It is reserved for the future Phase
8C browser application.

Do not copy Terraform state as evidence.

## Terraform-created smoke identity

Terraform creates the dedicated release-smoke service account:

`opsmind-release-smoke`

The Terraform resource intentionally creates that identity without generating a
client secret.

After apply, locate that service account in the dedicated OpsMind organization.

Before creating a key, verify:

- the service account is `opsmind-release-smoke`;
- its immutable user ID exactly matches the HCP Terraform `smoke_user_id`
  output;
- it belongs to the reviewed OpsMind organization;
- its project role assignment is read-only; and
- the assigned application role is exactly `opsmind.business.read`.

Do not grant:

- `opsmind.business.write`;
- `opsmind.recommendation.decide`;
- `ORG_OWNER`;
- `IAM_OWNER`; or
- any other administrator role

to the release-smoke identity.

## Release-smoke private key

Only after Terraform has created and granted the smoke service account, create
one private-key JWT credential for `opsmind-release-smoke`.

Create the key outside Terraform.

The private key must bypass Terraform state completely.

Use the service-account key-management interface and download the generated key
material securely.

Immediately verify, without logging private-key contents:

- the key's service-account/user ID matches `smoke_user_id`;
- the key ID is present;
- the private key is present;
- the credential belongs to `opsmind-release-smoke`.

ZITADEL private-key material must be treated as one-time-download secret
material. If it is lost, create a replacement key rather than attempting to
recover it.

## GitHub smoke-key handoff

Split the smoke credential into its required GitHub values.

Store the non-secret key identifier as the protected environment variable:

`ZITADEL_SMOKE_KEY_ID`

Store the private PEM key only as the protected environment secret:

`ZITADEL_SMOKE_PRIVATE_KEY`

Do not store the complete downloaded service-account JSON as a GitHub secret.

The protected `phase-8b` environment therefore receives these ZITADEL values:

| Name | GitHub kind | Producer |
| --- | --- | --- |
| `ZITADEL_ISSUER` | Variable | Verified instance issuer |
| `ZITADEL_PROJECT_ID` | Variable | HCP Terraform `project_id` output |
| `ZITADEL_SMOKE_USER_ID` | Variable | HCP Terraform `smoke_user_id` output |
| `ZITADEL_SMOKE_KEY_ID` | Variable | Owner-created smoke key |
| `ZITADEL_SMOKE_PRIVATE_KEY` | Secret | Owner-created smoke key |

The Terraform provider JWT Profile must not enter GitHub.

After successful handoff, remove any temporary unencrypted local copy of the
smoke credential.

## Runtime trust boundary

The smoke private key exists only to obtain a short-lived access token for the
protected release smoke test.

It is not an API signing key.

It is not a browser credential.

It is not a Render runtime secret.

It is not a Terraform provider credential.

The release helper requests only the reviewed scopes needed for:

- OpenID processing;
- the exact OpsMind project audience; and
- the project-specific role claim.

The resulting access token must contain the reviewed project audience and only
the read-only smoke role.

The protected API smoke may perform the authenticated business GET but must not
exercise business writes or recommendation decisions.

## Provider-key rotation

To rotate the Terraform provider credential:

1. create a replacement private-key JWT credential on `opsmind-terraform`;
2. securely download the replacement JWT Profile;
3. replace the sensitive HCP Terraform variable
   `zitadel_jwt_profile_json`;
4. run and review a credentialed HCP Terraform plan;
5. confirm the plan authenticates and proposes no unexpected resource changes;
6. revoke/delete the previous ZITADEL provider key;
7. remove any temporary local copy of the replacement credential.

Do not revoke the old provider key before the replacement has successfully
authenticated a reviewed plan.

## Smoke-key rotation

To rotate the release-smoke credential:

1. create a replacement private-key credential on `opsmind-release-smoke`;
2. verify its service-account/user ID;
3. replace GitHub environment variable `ZITADEL_SMOKE_KEY_ID`;
4. replace GitHub environment secret `ZITADEL_SMOKE_PRIVATE_KEY`;
5. run the bounded smoke-token/release validation;
6. revoke/delete the previous ZITADEL smoke key;
7. remove any temporary local copy.

Do not change `ZITADEL_SMOKE_USER_ID` during ordinary key rotation.

A service-account replacement is a different identity change and requires
separate review.

## Compromise and loss

If either private key is suspected compromised:

- stop affected applies or releases;
- create a replacement key;
- update only the authoritative secret store;
- verify the replacement;
- revoke the compromised key;
- review ZITADEL audit/event evidence as available.

If a private key file is merely lost but compromise is not suspected, create a
replacement. Do not attempt to reconstruct or recover a private key from
Terraform state, GitHub, logs, documentation, or repository history.

## Completion evidence

ZITADEL bootstrap is evidenced only when all of the following are true:

- one reviewed Free instance exists;
- the dedicated OpsMind organization and immutable ID are known;
- the exact issuer is verified;
- `opsmind-terraform` exists with organization-scoped bootstrap authority and
  no instance-wide `IAM_OWNER`;
- the Terraform provider JWT Profile exists only in the sensitive HCP workspace
  variable;
- the reviewed HCP Terraform plan/apply succeeds;
- the expected non-secret outputs are captured;
- `opsmind-release-smoke` exists with only the read application role;
- its private-key credential was created outside Terraform;
- the exact ZITADEL GitHub variables and smoke secret are handed to the
  protected `phase-8b` environment;
- no private key entered Terraform state, Git, Render, documentation, logs, or
  chat;
- no paid ZITADEL resource or automatic upgrade was accepted.

Until these conditions are observed, this document defines the ZITADEL
bootstrap procedure and does not claim that live Phase 8B ZITADEL resources
have been configured.
