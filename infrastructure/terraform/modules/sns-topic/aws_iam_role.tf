data "aws_iam_policy_document" "firehose-assume-role" {
  count = local.archive_enabled ? 1 : 0

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["firehose.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "firehose" {
  count = local.archive_enabled ? 1 : 0

  name               = "${local.name}-firehose"
  assume_role_policy = data.aws_iam_policy_document.firehose-assume-role[0].json
}

data "aws_iam_policy_document" "sns-delivery-assume-role" {
  count = local.archive_enabled ? 1 : 0

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["sns.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sns-delivery" {
  count = local.archive_enabled ? 1 : 0

  name               = "${local.name}-sns-delivery"
  assume_role_policy = data.aws_iam_policy_document.sns-delivery-assume-role[0].json
}
