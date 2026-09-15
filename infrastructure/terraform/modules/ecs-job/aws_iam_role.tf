data "aws_iam_policy_document" "scheduler-assume-role" {
  count = var.schedule != "" ? 1 : 0

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  count = var.schedule != "" ? 1 : 0

  name               = "${module.resource-name.name}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler-assume-role[0].json
}
