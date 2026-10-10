resource "aws_iam_role_policy_attachment" "managed-policies" {
  for_each = toset(var.policy_arns)

  role       = aws_iam_role.role.name
  policy_arn = each.value
}
