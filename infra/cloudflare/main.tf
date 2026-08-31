locals {
  production_environment = {
    VITE_OPSMIND_API_BASE_URL       = "https://opsmind-api-ru63.onrender.com"
    VITE_OPSMIND_ENVIRONMENT        = "production"
    VITE_OPSMIND_ZITADEL_ISSUER     = "https://opsmind-phase-8b-gl9aih.us1.zitadel.cloud"
    VITE_OPSMIND_ZITADEL_PROJECT_ID = "386124341898709869"
    VITE_OPSMIND_ZITADEL_CLIENT_ID  = "386124342116795580"
  }
}

resource "cloudflare_pages_project" "opsmind" {
  account_id        = var.cloudflare_account_id
  name              = var.pages_project_name
  production_branch = "main"

  build_config = {
    build_caching   = true
    build_command   = "npm run build"
    destination_dir = "dist"
    root_dir        = "frontend"
  }

  deployment_configs = {
    preview = {
      fail_open = true
    }

    production = {
      fail_open = true

      env_vars = {
        for key, value in local.production_environment : key => {
          type  = "plain_text"
          value = value
        }
      }
    }
  }

  source = {
    type = "github"
    config = {
      owner                          = "AnishPaudyal"
      repo_name                      = "opsmind"
      production_branch              = "main"
      production_deployments_enabled = false
      preview_deployment_setting     = "none"
      pr_comments_enabled            = false
    }
  }
}
