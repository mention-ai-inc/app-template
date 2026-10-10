data "aws_iam_policy_document" "assume-role" {
  dynamic "statement" {
    for_each = length(var.trusted_services) > 0 ? [1] : []

    content {
      effect  = "Allow"
      actions = ["sts:AssumeRole"]

      principals {
        type        = "Service"
        identifiers = var.trusted_services
      }
    }
  }

  dynamic "statement" {
    for_each = length(concat(var.assumable_by_role_arns, var.assumable_by_user_arns)) > 0 ? [1] : []

    content {
      effect  = "Allow"
      actions = ["sts:AssumeRole", "sts:TagSession"]

      principals {
        type        = "AWS"
        identifiers = concat(var.assumable_by_role_arns, var.assumable_by_user_arns)
      }
    }
  }
}

resource "aws_iam_role" "role" {
  name                 = var.role_name
  assume_role_policy   = data.aws_iam_policy_document.assume-role.json
  permissions_boundary = var.permissions_boundary
}
