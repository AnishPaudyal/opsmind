variable "zitadel_domain" {
  description = "Hostname of the owner-bootstrapped ZITADEL Cloud instance."
  type        = string

  validation {
    condition = (
      length(var.zitadel_domain) <= 253
      && lower(var.zitadel_domain) == var.zitadel_domain
      && trimspace(var.zitadel_domain) == var.zitadel_domain
      && endswith(var.zitadel_domain, ".zitadel.cloud")
      && alltrue([
        for label in split(".", var.zitadel_domain) :
        length(label) >= 1
        && length(label) <= 63
        && can(regex(
          "^[a-z0-9]([a-z0-9-]*[a-z0-9])?$",
          label,
        ))
      ])
    )
    error_message = "zitadel_domain must be one lowercase *.zitadel.cloud hostname."
  }
}

variable "zitadel_org_id" {
  description = "ID of the owner-bootstrapped ZITADEL organization."
  type        = string

  validation {
    condition     = length(trimspace(var.zitadel_org_id)) > 0
    error_message = "zitadel_org_id must not be empty."
  }
}

variable "zitadel_jwt_profile_json" {
  description = "Sensitive owner-created JWT Profile credential used only by the ZITADEL Terraform provider."
  type        = string
  sensitive   = true

  validation {
    condition     = length(trimspace(var.zitadel_jwt_profile_json)) > 0
    error_message = "zitadel_jwt_profile_json must not be empty."
  }
}

variable "portfolio_operator_user_id" {
  description = "Public numeric ZITADEL user ID for the owner-managed, non-administrator human portfolio operator; this is not a credential."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.portfolio_operator_user_id))
    error_message = "portfolio_operator_user_id must be a non-empty numeric ZITADEL user ID."
  }
}

variable "spa_redirect_uris" {
  description = "Reviewed redirect URIs for the OpsMind User Agent application."
  type        = set(string)

  default = [
    "https://opsmind-app.pages.dev/auth/callback",
  ]

  validation {
    condition     = length(var.spa_redirect_uris) > 0
    error_message = "At least one SPA redirect URI is required."
  }
}

variable "spa_post_logout_redirect_uris" {
  description = "Reviewed post-logout URIs for the OpsMind User Agent application."
  type        = set(string)

  default = [
    "https://opsmind-app.pages.dev/",
  ]

  validation {
    condition     = length(var.spa_post_logout_redirect_uris) > 0
    error_message = "At least one SPA post-logout redirect URI is required."
  }
}

variable "spa_additional_origins" {
  description = "Reviewed browser origins allowed for the OpsMind User Agent application."
  type        = set(string)

  default = [
    "https://opsmind-app.pages.dev",
  ]
}
