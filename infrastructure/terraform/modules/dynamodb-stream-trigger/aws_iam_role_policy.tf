data "aws_iam_policy_document" "pipe" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:DescribeStream",
      "dynamodb:GetRecords",
      "dynamodb:GetShardIterator",
      "dynamodb:ListStreams",
    ]
    resources = [var.table_stream_arn]
  }

  statement {
    effect    = "Allow"
    actions   = ["sqs:SendMessage", "sqs:GetQueueAttributes", "sqs:GetQueueUrl"]
    resources = [aws_sqs_queue.trigger.arn, aws_sqs_queue.dead-letter.arn]
  }
}

resource "aws_iam_role_policy" "pipe" {
  name   = "${module.queue-name.name}-pipe"
  role   = aws_iam_role.pipe.id
  policy = data.aws_iam_policy_document.pipe.json
}
