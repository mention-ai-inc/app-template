module "static-assets" {
  source = "../../modules/s3-bucket"

  name_prefix         = local.bucket_name_prefix
  feature_environment = ""
  bucket_name         = "static-assets"
  force_destroy       = false
}

module "load-balancer-logs" {
  source = "../../modules/s3-bucket"

  name_prefix         = local.bucket_name_prefix
  feature_environment = ""
  bucket_name         = "load-balancer-logs"
  force_destroy       = false
}

data "aws_elb_service_account" "current" {}

data "aws_iam_policy_document" "load-balancer-logs" {
  statement {
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["${module.load-balancer-logs.bucket_arn}/*"]

    principals {
      type        = "AWS"
      identifiers = [data.aws_elb_service_account.current.arn]
    }
  }

  statement {
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["${module.load-balancer-logs.bucket_arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["logdelivery.elasticloadbalancing.amazonaws.com"]
    }
  }
}

resource "aws_s3_bucket_policy" "load-balancer-logs" {
  bucket = module.load-balancer-logs.bucket_name
  policy = data.aws_iam_policy_document.load-balancer-logs.json
}

output "static_assets_bucket_name" {
  value = module.static-assets.bucket_name
}

output "static_assets_bucket_arn" {
  value = module.static-assets.bucket_arn
}

output "load_balancer_logs_bucket_name" {
  value = module.load-balancer-logs.bucket_name
}

output "bucket_name_prefix" {
  value = local.bucket_name_prefix
}
