locals {
  base_name        = join("", [var.feature_environment, replace(var.service_name, "_", "-"), "-t-", replace(var.trigger_name, "_", "-")])
  partition_prefix = "${var.feature_environment}${var.service_name}_${var.collection}#"
}

module "queue-name" {
  source     = "../resource-name"
  full_name  = local.base_name
  max_length = 77
}

resource "aws_sqs_queue" "dead-letter" {
  name                       = "${module.queue-name.name}-dl"
  message_retention_seconds  = var.dead_letter_retention_seconds
  visibility_timeout_seconds = var.timeout_seconds
  sqs_managed_sse_enabled    = true
}

resource "aws_sqs_queue" "trigger" {
  name                       = module.queue-name.name
  visibility_timeout_seconds = var.timeout_seconds
  message_retention_seconds  = var.message_retention_seconds
  receive_wait_time_seconds  = 20
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dead-letter.arn
    maxReceiveCount     = var.max_delivery_attempts
  })
}

resource "aws_sqs_queue_redrive_allow_policy" "dead-letter" {
  queue_url = aws_sqs_queue.dead-letter.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.trigger.arn]
  })
}
