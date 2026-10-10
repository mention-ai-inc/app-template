resource "aws_sns_topic_subscription" "listener" {
  for_each = local.indexed_subscriptions

  topic_arn            = var.topic_arns[each.value.topic_name]
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.listener[each.key].arn
  raw_message_delivery = true
  filter_policy_scope  = "MessageAttributes"
  filter_policy        = jsonencode(local.filter_policies[each.key])

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dead-letter.arn
  })
}
