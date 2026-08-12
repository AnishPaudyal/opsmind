# Phase 8B HCP Terraform bootstrap and run contract

## Purpose

This runbook defines the owner-controlled HCP Terraform workspace used for the
Phase 8B ZITADEL configuration in `infra/zitadel`.

It is an operational companion to:

- `phase-8b-cloud-backend-gate.md`;
- ADR-0007; and
- `infra/zitadel/README.md`.

The workspace is a control-plane bootstrap exception. Terraform does not manage
the HCP Terraform organization, project, VCS connection, workspace, or its own
bootstrap credential.

## Authority boundary

HCP Terraform owns:

- remote Terraform state for `infra/zitadel`;
- serialized remote runs and run history;
- the credentialed ZITADEL plan;
- owner-reviewed applies; and
- workspace-scoped Terraform variable values.

GitHub Actions owns only credential-free Terraform formatting and validation.

The repository owner owns:

- HCP Terraform account and organization bootstrap;
- the HCP Terraform GitHub App authorization;
- workspace creation and settings;
- workspace variables;
- review and approval of applies; and
- provider credential rotation.

HCP Terraform must not manage:

- Neon;
- Render;
- GitHub deployment environments;
- database migrations;
- GHCR release images;
- the ZITADEL smoke private key; or
- Phase 8C frontend infrastructure.

## Preconditions

Do not create the workspace until all of the following are true:

1. the Phase 8B Terraform source under `infra/zitadel` has been reviewed;
2. repository Terraform quality is green;
3. the owner-approved ZITADEL Cloud instance and bootstrap organization exist;
4. the owner-created Terraform service-account JWT Profile credential exists;
5. no payment, paid plan, trial conversion, or automatic upgrade is required;
6. the repository remains the only repository authorized for this HCP Terraform
   VCS connection.

Never paste provider credentials into GitHub issues, pull requests, chat,
screenshots, Terraform source, `.tfvars`, workflow YAML, or documentation.

## Workspace contract

Create exactly one Phase 8B VCS-driven workspace with the following reviewed
settings.

| Setting | Required value |
| --- | --- |
| VCS repository | This OpsMind repository only |
| VCS branch | `main` |
| Terraform working directory | `infra/zitadel` |
| Execution mode | Remote |
| Terraform version | `1.15.8` exactly |
| Apply method | Manual apply |
| Auto apply | Disabled |
| Automatic speculative plans | Disabled |
| Automatic run filtering | Retain the working-directory filter; do not select always-trigger |
| HCP Terraform agents | None |
| Run tasks | None |
| SSH key | None |
| Remote-state sharing | No other workspace |

Do not add a `cloud` block or HCP backend configuration to the Terraform source.
The workspace's VCS integration and working-directory setting are the selected
execution path.

Do not create an HCP Terraform API token for GitHub Actions. The repository's
Terraform quality workflow remains credential-free.

## Workspace variables

Create exactly these required workspace-specific **Terraform** variables.

| Key | Category | Sensitive | HCL | Source |
| --- | --- | --- | --- | --- |
| `zitadel_domain` | Terraform | No | No | Owner-bootstrapped ZITADEL Cloud hostname |
| `zitadel_org_id` | Terraform | No | No | Owner-bootstrapped ZITADEL organization ID |
| `zitadel_jwt_profile_json` | Terraform | Yes | No | Owner-created Terraform service-account JWT Profile JSON |

For `zitadel_jwt_profile_json`, enable the HCP Terraform **Sensitive** setting
before saving the credential.

Do not copy the value into a variable description. Descriptions are metadata,
not secret storage.

Do not configure these optional variables during Phase 8B unless the committed
defaults are deliberately changed and reviewed:

- `spa_redirect_uris`;
- `spa_post_logout_redirect_uris`; and
- `spa_additional_origins`.

Their current localhost values are committed Phase 8B placeholders for the
future Phase 8C SPA.

The following values must never become HCP Terraform workspace variables:

- ZITADEL smoke private key;
- Neon pooled runtime URL;
- Neon direct migration URL;
- Render deploy-hook URL;
- Render runtime secrets; or
- GitHub deployment secrets.

## VCS and run behavior

The workspace watches `main`.

The working directory is `infra/zitadel`, so ordinary VCS-triggered runs should
be scoped to changes relevant to that Terraform configuration. Do not configure
the workspace to run for every repository change.

Automatic speculative plans for pull requests must remain disabled. Pull
requests receive credential-free `terraform fmt`, backend-free initialization,
and `terraform validate` from GitHub Actions instead.

A reviewed change merged to `main` may start the credentialed HCP Terraform
plan. Because manual apply is required, a successful plan must stop for owner
review before any infrastructure mutation.

Never enable auto apply for this workspace.

## First plan review

For an empty Phase 8B workspace managing no pre-existing OpsMind project
resources, the current configuration is expected to propose seven resources:

- one `zitadel_project`;
- three `zitadel_project_role` resources;
- one `zitadel_application_oidc`;
- one `zitadel_machine_user`; and
- one `zitadel_user_grant`.

Before approving the first apply, verify all of the following:

- no destroy actions;
- no unexpected replacements;
- no resource outside the official ZITADEL provider;
- exactly three project roles:
  - `opsmind.business.read`;
  - `opsmind.business.write`;
  - `opsmind.recommendation.decide`;
- the release-smoke identity receives only `opsmind.business.read`;
- the SPA is a public User Agent application using Authorization Code;
- JWT access tokens remain selected;
- no `zitadel_machine_key` resource exists;
- no smoke private key is generated, stored, or output;
- no Neon, Render, Cloudflare, AWS, GitHub, migration, or release resource is
  present.

If any unexpected resource, permission, destroy, replacement, credential,
billing prompt, or paid-plan requirement appears, stop without applying.

## First apply and handoff

After the plan is reviewed and all zero-cost and authority checks remain valid,
the owner may confirm the manual apply.

After the successful apply, capture only the non-secret outputs required for
the next controlled bootstrap steps:

- `project_id`;
- `project_role_claim`;
- `spa_client_id`;
- `smoke_user_id`; and
- `smoke_role_keys`.

Do not copy Terraform state or the provider JWT Profile into repository files.

The smoke authentication key is created separately after the machine identity
exists. Its private key must bypass Terraform state and later be stored only in
the protected GitHub `phase-8b` environment.

## Normal operating rule

For later Terraform changes:

1. change reviewed source under `infra/zitadel`;
2. require the GitHub Terraform quality check to pass;
3. merge the reviewed change to `main`;
4. inspect the HCP Terraform plan;
5. reject unexpected changes;
6. manually apply only the intended plan.

Local development remains limited to formatting, provider initialization
without a backend, dependency locking, and static validation.

Do not run a real local `terraform apply`.
