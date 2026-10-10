data "aws_iam_policy_document" "firehose" {
  count = local.archive_enabled ? 1 : 0

  statement {
    effect = "Allow"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:GetBucketLocation",
      "s3:GetObject",
      "s3:ListBucket",
      "s3:ListBucketMultipartUploads",
      "s3:PutObject",
    ]
    resources = [var.archive_bucket_arn, "${var.archive_bucket_arn}/*"]
  }

  statement {
    effect    = "Allow"
    actions   = ["logs:PutLogEvents", "logs:CreateLogStream"]
    resources = ["${aws_cloudwatch_log_group.firehose[0].arn}:*"]
  }
}

resource "aws_iam_role_policy" "firehose" {
  count = local.archive_enabled ? 1 : 0

  name   = "${local.name}-firehose"
  role   = aws_iam_role.firehose[0].id
  policy = data.aws_iam_policy_document.firehose[0].json
}

data "aws_iam_policy_document" "sns-delivery" {
  count = local.archive_enabled ? 1 : 0

  statement {
    effect    = "Allow"
    actions   = ["firehose:DescribeDeliveryStream", "firehose:PutRecord", "firehose:PutRecordBatch"]
    resources = [aws_kinesis_firehose_delivery_stream.archive[0].arn]
  }
}

resource "aws_iam_role_policy" "sns-delivery" {
  count = local.archive_enabled ? 1 : 0

  name   = "${local.name}-sns-delivery"
  role   = aws_iam_role.sns-delivery[0].id
  policy = data.aws_iam_policy_document.sns-delivery[0].json
}
