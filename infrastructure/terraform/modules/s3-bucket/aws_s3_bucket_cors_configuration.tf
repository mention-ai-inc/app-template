resource "aws_s3_bucket_cors_configuration" "bucket" {
  count = length(var.cors_origins) > 0 ? 1 : 0

  bucket = aws_s3_bucket.bucket.id

  cors_rule {
    allowed_origins = var.cors_origins
    allowed_methods = ["GET", "PUT"]
    allowed_headers = ["Content-Type"]
    max_age_seconds = 3600
  }
}
