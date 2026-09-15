data "aws_iam_policy_document" "listener" {
  for_each = local.indexed_subscriptions

  statement {
    sid       = "AllowTopicDelivery"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.listener[each.key].arn]

    principals {
      type        = "Service"
      identifiers = ["sns.amazonaws.com"]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [var.topic_arns[each.value.topic_name]]
    }
  }

  dynamic "statement" {
    for_each = length(var.reader_role_arns) > 0 ? [1] : []

    content {
      sid    = "AllowListenerRead"
      effect = "Allow"
      actions = [
        "sqs:ChangeMessageVisibility",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:GetQueueUrl",
        "sqs:ReceiveMessage",
      ]
      resources = [aws_sqs_queue.listener[each.key].arn]

      principals {
        type        = "AWS"
        identifiers = var.reader_role_arns
      }
    }
  }
}

resource "aws_sqs_queue_policy" "listener" {
  for_each = local.indexed_subscriptions

  queue_url = aws_sqs_queue.listener[each.key].id
  policy    = data.aws_iam_policy_document.listener[each.key].json
}
