data "aws_iam_policy_document" "assume-role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider_host}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "${var.oidc_provider_host}:sub"
      values   = [for pattern in var.subject_patterns : "repo:${var.github_repo}:${pattern}"]
    }
  }
}

resource "aws_iam_role" "role" {
  name                 = var.role_name
  assume_role_policy   = data.aws_iam_policy_document.assume-role.json
  max_session_duration = var.maximum_session_duration_seconds
}
