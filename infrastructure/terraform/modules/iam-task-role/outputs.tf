output "arn" {
  description = "ARN of the role, which is what task definitions and trust policies reference."
  value       = aws_iam_role.role.arn
}

output "name" {
  description = "Name of the role."
  value       = aws_iam_role.role.name
}

output "unique_id" {
  description = "Stable identifier of the role, unchanged when the role is renamed."
  value       = aws_iam_role.role.unique_id
}
