module "cache-buckets" {
  source   = "../../modules/s3-bucket"
  for_each = var.services

  name_prefix             = local.bucket_name_prefix
  feature_environment     = local.feature_environment
  service                 = each.key
  bucket_name             = "cache"
  cors_origins            = ["https://${local.feature_environment}${var.app_domain}"]
  reader_writer_role_arns = [module.service-task-role[each.key].arn]
}

module "event-archive" {
  source = "../../modules/s3-bucket"

  name_prefix         = local.bucket_name_prefix
  feature_environment = local.feature_environment
  bucket_name         = "event-archive"
}

resource "aws_s3_bucket" "audit-archive" {
  bucket              = "${local.bucket_name_prefix}--${local.feature_environment}audit-archive"
  force_destroy       = !local.is_production
  object_lock_enabled = local.is_production
}

resource "aws_s3_bucket_versioning" "audit-archive" {
  bucket = aws_s3_bucket.audit-archive.id

  versioning_configuration {
    status = local.is_production ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_public_access_block" "audit-archive" {
  bucket = aws_s3_bucket.audit-archive.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit-archive" {
  bucket = aws_s3_bucket.audit-archive.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_object_lock_configuration" "audit-archive" {
  count = local.is_production ? 1 : 0

  bucket = aws_s3_bucket.audit-archive.id

  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = var.audit_retention_days
    }
  }

  depends_on = [aws_s3_bucket_versioning.audit-archive]
}

resource "aws_s3_bucket_lifecycle_configuration" "audit-archive" {
  bucket = aws_s3_bucket.audit-archive.id

  rule {
    id     = "expire-after-retention-window"
    status = "Enabled"

    filter {}

    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    expiration {
      days = var.audit_retention_days
    }
  }
}

resource "aws_glue_catalog_database" "event-export" {
  name        = "${local.feature_environment}event_export"
  description = "Archived event streams, queryable with Athena."
}

resource "aws_glue_catalog_database" "audit-export" {
  name        = "${local.feature_environment}audit_export"
  description = "Archived audit events, retained per policy and queryable with Athena."
}

data "aws_iam_policy_document" "static-assets-reader" {
  statement {
    effect  = "Allow"
    actions = ["s3:GetObject", "s3:ListBucket"]
    resources = [
      data.terraform_remote_state.operations.outputs.static_assets_bucket_arn,
      "${data.terraform_remote_state.operations.outputs.static_assets_bucket_arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "static-assets-reader" {
  for_each = var.services

  name   = "${local.feature_environment}${each.key}-static-assets"
  role   = module.service-task-role[each.key].name
  policy = data.aws_iam_policy_document.static-assets-reader.json
}
