output "id" {
  description = "An identifier for the role with the format `projects/{{project}}/roles/{{role_id}}`."
  value       = google_project_iam_custom_role.custom-iam-role.id
}
