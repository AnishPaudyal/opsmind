# OpsMind ZITADEL Terraform

This directory owns only the provider-supported ZITADEL resources authorized by
Phase 8B:

- the OpsMind project;
- the three exact application roles;
- the future public User Agent / SPA OIDC application;
- the dedicated release-smoke machine identity; and
- its single `opsmind.business.read` grant.

It does not own:

- ZITADEL Cloud instance or bootstrap organization creation;
- the Terraform provider credential;
- any smoke private key;
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
