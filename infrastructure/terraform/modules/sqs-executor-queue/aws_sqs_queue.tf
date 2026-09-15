module "queue-name" {
  source     = "../resource-name"
  full_name  = join("", [var.feature_environment, replace(var.service_name, "_", "-"), "-c-", replace(var.command_name, "_", "-")])
  max_length = 75
}

resource "aws_sqs_queue" "dead-letter" {
  name                       = "${module.queue-name.name}-dl"
  message_retention_seconds  = var.dead_letter_retention_seconds
  sqs_managed_sse_enabled    = true
  visibility_timeout_seconds = var.visibility_timeout_seconds
}

resource "aws_sqs_queue" "queue" {
  name                       = module.queue-name.name
  visibility_timeout_seconds = var.visibility_timeout_seconds
  message_retention_seconds  = var.message_retention_seconds
  receive_wait_time_seconds  = 20
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dead-letter.arn
    maxReceiveCount     = var.max_task_attempts
  })
}

resource "aws_sqs_queue_redrive_allow_policy" "dead-letter" {
  queue_url = aws_sqs_queue.dead-letter.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.queue.arn]
  })
}
