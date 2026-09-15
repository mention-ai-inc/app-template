locals {
  base_name = join("", [var.feature_environment, replace(var.service_name, "_", "-"), "-", replace(var.listener_name, "_", "-")])
  indexed_subscriptions = {
    for index, subscription in var.subscriptions : tostring(index) => subscription
  }
  filter_policies = {
    for index, subscription in local.indexed_subscriptions : index => merge(
      {
        service = split("|", subscription.source_service_name)
        event   = split("|", subscription.event_name)
      },
      subscription.model_name == null || subscription.model_name == "" ? {} : {
        model_name = split("|", subscription.model_name)
      },
    )
  }
}

module "dead-letter-queue-name" {
  source     = "../resource-name"
  full_name  = "${local.base_name}-dl"
  max_length = 80
}

module "queue-name" {
  source     = "../resource-name"
  for_each   = local.indexed_subscriptions
  full_name  = "${local.base_name}-${each.key}"
  max_length = 80
}

resource "aws_sqs_queue" "dead-letter" {
  name                       = module.dead-letter-queue-name.name
  message_retention_seconds  = var.dead_letter_retention_seconds
  visibility_timeout_seconds = var.timeout_seconds
  sqs_managed_sse_enabled    = true
}

resource "aws_sqs_queue" "listener" {
  for_each = local.indexed_subscriptions

  name                       = module.queue-name[each.key].name
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
    sourceQueueArns   = [for queue in aws_sqs_queue.listener : queue.arn]
  })
}
