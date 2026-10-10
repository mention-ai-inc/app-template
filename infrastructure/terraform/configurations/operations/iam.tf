module "permissions" {
  source = "../../modules/permissions"

  services = []
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

module "github-actions-role" {
  source = "../../modules/github-oidc-role"

  role_name         = "github-actions"
  oidc_provider_arn = aws_iam_openid_connect_provider.github.arn
  github_repo       = var.github_repo
  actions = concat(
    module.permissions.github_actions_actions.host,
    module.permissions.github_actions_actions.feature_only,
    module.permissions.github_actions_actions.operations,
  )
}

module "terraform-role" {
  source = "../../modules/github-oidc-role"

  role_name         = "terraform"
  oidc_provider_arn = aws_iam_openid_connect_provider.github.arn
  github_repo       = var.github_repo
  policy_arns       = ["arn:aws:iam::aws:policy/AdministratorAccess"]

  additionally_assumable_by = ["arn:aws:iam::${var.account_id}:root"]
}

resource "aws_iam_group" "engineers" {
  name = "engineers"
}

data "aws_iam_policy_document" "engineers" {
  statement {
    effect    = "Allow"
    actions   = module.permissions.engineers_service_actions
    resources = ["*"]
  }

  statement {
    effect  = "Allow"
    actions = ["iam:PassRole"]
    resources = [
      "arn:aws:iam::${local.account_id}:role/*admin-s",
      "arn:aws:iam::${local.account_id}:role/*admin-execution",
    ]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_policy" "engineers" {
  name        = "engineers"
  description = "What an engineer may reach directly, without assuming the terraform role."
  policy      = data.aws_iam_policy_document.engineers.json
}

resource "aws_iam_group_policy_attachment" "engineers" {
  group      = aws_iam_group.engineers.name
  policy_arn = aws_iam_policy.engineers.arn
}

data "aws_iam_policy_document" "engineers-assume-terraform" {
  statement {
    effect    = "Allow"
    actions   = ["sts:AssumeRole"]
    resources = [module.terraform-role.arn]
  }
}

resource "aws_iam_policy" "engineers-assume-terraform" {
  name        = "engineers-assume-terraform"
  description = "Lets an engineer run the terraform targets and create feature environments locally."
  policy      = data.aws_iam_policy_document.engineers-assume-terraform.json
}

resource "aws_iam_group_policy_attachment" "engineers-assume-terraform" {
  group      = aws_iam_group.engineers.name
  policy_arn = aws_iam_policy.engineers-assume-terraform.arn
}

output "github_actions_role_arn" {
  value = module.github-actions-role.arn
}

output "terraform_role_arn" {
  value = module.terraform-role.arn
}

output "engineers_group_name" {
  value = aws_iam_group.engineers.name
}

output "account_id" {
  value = local.account_id
}
