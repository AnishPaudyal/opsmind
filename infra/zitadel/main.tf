locals {
  project_roles = {
    "opsmind.business.read" = {
      display_name = "OpsMind business read"
    }
    "opsmind.business.write" = {
      display_name = "OpsMind business write"
    }
    "opsmind.recommendation.decide" = {
      display_name = "OpsMind recommendation decision"
    }
  }
}

resource "zitadel_project" "opsmind" {
  org_id = var.zitadel_org_id
  name   = "OpsMind"

  # Roles are requested explicitly through the reviewed project-role scope.
  # Authentication itself must not require a role, so valid but unauthorized
  # principals can reach OpsMind's existing generic 403 boundary.
  project_role_assertion = false
  project_role_check     = false
  has_project_check      = false
}

resource "zitadel_project_role" "opsmind" {
  for_each = local.project_roles

  org_id       = var.zitadel_org_id
  project_id   = zitadel_project.opsmind.id
  role_key     = each.key
  display_name = each.value.display_name
}

resource "zitadel_application_oidc" "spa" {
  org_id     = var.zitadel_org_id
  project_id = zitadel_project.opsmind.id
  name       = "OpsMind SPA"

  redirect_uris             = sort(tolist(var.spa_redirect_uris))
  post_logout_redirect_uris = sort(tolist(var.spa_post_logout_redirect_uris))
  additional_origins        = sort(tolist(var.spa_additional_origins))

  response_types = [
    "OIDC_RESPONSE_TYPE_CODE",
  ]

  grant_types = [
    "OIDC_GRANT_TYPE_AUTHORIZATION_CODE",
  ]

  app_type         = "OIDC_APP_TYPE_USER_AGENT"
  auth_method_type = "OIDC_AUTH_METHOD_TYPE_NONE"
  version          = "OIDC_VERSION_1_0"

  # Phase 8B intentionally permits localhost placeholders. Phase 8C must
  # replace/review these before declaring the browser integration complete.
  dev_mode = true

  # OpsMind validates JWT access tokens locally through the trusted JWKS path.
  access_token_type = "OIDC_TOKEN_TYPE_JWT"

  # Authorization data is requested deliberately through scopes instead of
  # being inserted into every token automatically.
  access_token_role_assertion = false
  id_token_role_assertion     = false
  id_token_userinfo_assertion = false

  skip_native_app_success_page = false
}

resource "zitadel_machine_user" "release_smoke" {
  org_id      = var.zitadel_org_id
  user_name   = "opsmind-release-smoke"
  name        = "OpsMind Release Smoke"
  description = "Least-privilege identity for the protected Phase 8B authenticated read-only smoke."

  access_token_type = "ACCESS_TOKEN_TYPE_JWT"
  with_secret       = false
}

resource "zitadel_user_grant" "release_smoke_read" {
  org_id     = var.zitadel_org_id
  project_id = zitadel_project.opsmind.id
  user_id    = zitadel_machine_user.release_smoke.id

  role_keys = [
    zitadel_project_role.opsmind["opsmind.business.read"].role_key,
  ]
}
