resource "aws_s3_bucket" "bucket" {
  bucket        = "${var.name_prefix}--${var.feature_environment}${var.service != "" ? "${var.service}-" : ""}${var.bucket_name}"
  force_destroy = var.force_destroy
}
