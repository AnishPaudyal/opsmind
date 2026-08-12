output "project_id" {
  description = "Immutable ZITADEL project ID used as the OpsMind API audience."
  value       = zitadel_project.opsmind.id
}

output "project_role_claim" {
  description = "Exact project-specific ZITADEL role claim consumed by OpsMind."
  value       = "urn:zitadel:iam:org:project:${zitadel_project.opsmind.id}:roles"
}

output "spa_client_id" {
  description = "Public OIDC client ID for the future Phase 8C browser application."
  value       = zitadel_application_oidc.spa.client_id
}

output "smoke_user_id" {
  description = "Machine-user ID consumed by the bounded release smoke-token helper."
  value       = zitadel_machine_user.release_smoke.id
}

output "smoke_role_keys" {
  description = "Exact project roles assigned to the release smoke identity."
  value       = zitadel_user_grant.release_smoke_read.role_keys
}
