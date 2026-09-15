output "service_name" {
  description = "The name of the service being deployed."
  value       = var.service_name
}

output "cloud_run_name" {
  description = "The name of the deployed ECS service. Named cloud_run_name because the deployment CLI on the base branch reads this field by that name for every provider."
  value       = aws_ecs_service.server.name
}

output "task_definition_family" {
  description = "The task definition family a deploy registers new revisions of."
  value       = aws_ecs_task_definition.server.family
}

output "target_group_arn" {
  description = "The target group the load balancer routes this server's traffic to."
  value       = var.target_group_arn
}

output "security_group_id" {
  description = "The security group the server's tasks run with."
  value       = aws_security_group.server.id
}
