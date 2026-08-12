terraform {
  required_version = ">= 1.9.0, < 2.0.0"

  required_providers {
    zitadel = {
      source  = "zitadel/zitadel"
      version = "= 3.3.0"
    }
  }
}

provider "zitadel" {
  domain                   = var.zitadel_domain
  port                     = "443"
  insecure                 = false
  insecure_skip_verify_tls = false
  jwt_profile_json         = var.zitadel_jwt_profile_json
}
