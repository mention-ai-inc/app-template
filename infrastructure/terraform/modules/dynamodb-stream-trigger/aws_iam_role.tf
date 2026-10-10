data "aws_iam_policy_document" "pipe-assume-role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["pipes.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "pipe" {
  name               = "${module.queue-name.name}-pipe"
  assume_role_policy = data.aws_iam_policy_document.pipe-assume-role.json
}
