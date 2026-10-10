data "aws_iam_policy_document" "queue" {
  count = length(var.reader_writer_role_arns) > 0 ? 1 : 0

  statement {
    effect = "Allow"
    actions = [
      "sqs:ChangeMessageVisibility",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ReceiveMessage",
      "sqs:SendMessage",
    ]
    resources = [aws_sqs_queue.queue.arn]

    principals {
      type        = "AWS"
      identifiers = var.reader_writer_role_arns
    }
  }
}

resource "aws_sqs_queue_policy" "queue" {
  count = length(var.reader_writer_role_arns) > 0 ? 1 : 0

  queue_url = aws_sqs_queue.queue.id
  policy    = data.aws_iam_policy_document.queue[0].json
}
