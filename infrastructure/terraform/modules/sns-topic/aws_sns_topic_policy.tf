data "aws_iam_policy_document" "topic" {
  count = length(var.publisher_role_arns) > 0 ? 1 : 0

  statement {
    effect    = "Allow"
    actions   = ["sns:Publish", "sns:GetTopicAttributes"]
    resources = [aws_sns_topic.topic.arn]

    principals {
      type        = "AWS"
      identifiers = var.publisher_role_arns
    }
  }
}

resource "aws_sns_topic_policy" "topic" {
  count = length(var.publisher_role_arns) > 0 ? 1 : 0

  arn    = aws_sns_topic.topic.arn
  policy = data.aws_iam_policy_document.topic[0].json
}
