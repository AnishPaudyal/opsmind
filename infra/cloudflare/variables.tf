variable "cloudflare_account_id" {
  description = "Public identifier of the owner-controlled Cloudflare account."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-f]{32}$", var.cloudflare_account_id))
    error_message = "cloudflare_account_id must be one lowercase 32-character hexadecimal identifier."
  }
}

variable "cloudflare_api_token" {
  description = "Sensitive Pages Read/Write token used only by the Cloudflare Terraform provider."
  type        = string
  sensitive   = true

  validation {
    condition     = length(trimspace(var.cloudflare_api_token)) > 0
    error_message = "cloudflare_api_token must not be empty."
  }
}

variable "pages_project_name" {
  description = "Available public Cloudflare Pages project name selected by the repository owner."
  type        = string

  validation {
    condition = (
      length(var.pages_project_name) >= 1
      && length(var.pages_project_name) <= 58
      && can(regex(
        "^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$",
        var.pages_project_name,
      ))
    )
    error_message = "pages_project_name must be 1-58 lowercase letters, digits, or hyphens and cannot start or end with a hyphen."
  }
}
