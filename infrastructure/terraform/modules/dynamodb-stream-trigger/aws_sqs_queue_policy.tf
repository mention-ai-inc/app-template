data "aws_iam_policy_document" "trigger" {
  count = length(var.reader_role_arns) > 0 ? 1 : 0

  statement {
    effect = "Allow"
    actions = [
      "sqs:ChangeMessageVisibility",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ReceiveMessage",
    ]
    resources = [aws_sqs_queue.trigger.arn]

    principals {
      type        = "AWS"
      identifiers = var.reader_role_arns
    }
  }
}

resource "aws_sqs_queue_policy" "trigger" {
  count = length(var.reader_role_arns) > 0 ? 1 : 0

  queue_url = aws_sqs_queue.trigger.id
  policy    = data.aws_iam_policy_document.trigger[0].json
}
