output "pages_project_name" {
  description = "Public name of the Terraform-managed Cloudflare Pages project."
  value       = cloudflare_pages_project.opsmind.name
}

output "pages_origin" {
  description = "Provider-issued stable HTTPS origin captured for later exact-origin wiring."
  value       = "https://${cloudflare_pages_project.opsmind.subdomain}"
}
