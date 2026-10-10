data "aws_iam_policy_document" "granted-actions" {
  count = length(var.actions) > 0 ? 1 : 0

  statement {
    effect    = "Allow"
    actions   = var.actions
    resources = var.resources
  }
}

resource "aws_iam_role_policy" "granted-actions" {
  count = length(var.actions) > 0 ? 1 : 0

  name   = "${var.role_name}-actions"
  role   = aws_iam_role.role.id
  policy = data.aws_iam_policy_document.granted-actions[0].json
}
