output "cloud_run_name" {
  description = "The name of the deployed ECS service. Named cloud_run_name because the deployment CLI on the base branch reads this field by that name for every provider."
  value       = aws_ecs_service.pool.name
}

output "task_definition_family" {
  description = "The task definition family a deploy registers new revisions of."
  value       = aws_ecs_task_definition.pool.family
}

output "security_group_id" {
  description = "The security group the pool's tasks run with."
  value       = aws_security_group.pool.id
}
