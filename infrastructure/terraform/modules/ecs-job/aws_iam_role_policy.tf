data "aws_iam_policy_document" "scheduler" {
  count = var.schedule != "" ? 1 : 0

  statement {
    effect    = "Allow"
    actions   = ["ecs:RunTask"]
    resources = ["${aws_ecs_task_definition.job.arn_without_revision}:*"]

    condition {
      test     = "ArnLike"
      variable = "ecs:cluster"
      values   = [var.cluster_arn]
    }
  }

  statement {
    effect    = "Allow"
    actions   = ["iam:PassRole"]
    resources = [var.task_role_arn, var.execution_role_arn]
  }
}

resource "aws_iam_role_policy" "scheduler" {
  count = var.schedule != "" ? 1 : 0

  name   = "${module.resource-name.name}-scheduler"
  role   = aws_iam_role.scheduler[0].id
  policy = data.aws_iam_policy_document.scheduler[0].json
}
