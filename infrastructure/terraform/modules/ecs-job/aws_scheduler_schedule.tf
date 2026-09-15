resource "aws_scheduler_schedule" "job" {
  count = var.schedule != "" ? 1 : 0

  name                = "${module.resource-name.name}-schedule"
  description         = "Invocation schedule for the ${var.service_name} ${var.job_name} job."
  schedule_expression = var.schedule
  group_name          = "default"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = var.cluster_arn
    role_arn = aws_iam_role.scheduler[0].arn

    ecs_parameters {
      task_definition_arn     = aws_ecs_task_definition.job.arn_without_revision
      task_count              = var.task_count
      launch_type             = "FARGATE"
      platform_version        = "LATEST"
      propagate_tags          = "TASK_DEFINITION"
      enable_execute_command  = false
      enable_ecs_managed_tags = true

      network_configuration {
        subnets          = var.subnet_ids
        security_groups  = [aws_security_group.job.id]
        assign_public_ip = false
      }
    }

    retry_policy {
      maximum_retry_attempts       = var.max_retries
      maximum_event_age_in_seconds = var.task_timeout_seconds
    }
  }
}
