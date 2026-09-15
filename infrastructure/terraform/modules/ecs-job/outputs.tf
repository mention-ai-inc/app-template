output "job_name" {
  description = "The task definition family a run of this job launches. Deploys register new revisions of it and the scheduler always runs the latest."
  value       = aws_ecs_task_definition.job.family
}

output "task_definition_arn" {
  description = "ARN of the job's task definition, without a revision."
  value       = aws_ecs_task_definition.job.arn_without_revision
}

output "security_group_id" {
  description = "The security group the job's tasks run with."
  value       = aws_security_group.job.id
}
