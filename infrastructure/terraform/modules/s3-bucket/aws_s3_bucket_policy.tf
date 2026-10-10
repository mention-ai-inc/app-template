data "aws_iam_policy_document" "bucket" {
  count = length(var.reader_writer_role_arns) > 0 ? 1 : 0

  statement {
    effect = "Allow"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = ["${aws_s3_bucket.bucket.arn}/*"]

    principals {
      type        = "AWS"
      identifiers = var.reader_writer_role_arns
    }
  }

  statement {
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.bucket.arn]

    principals {
      type        = "AWS"
      identifiers = var.reader_writer_role_arns
    }
  }
}

resource "aws_s3_bucket_policy" "bucket" {
  count = length(var.reader_writer_role_arns) > 0 ? 1 : 0

  bucket = aws_s3_bucket.bucket.id
  policy = data.aws_iam_policy_document.bucket[0].json

  depends_on = [aws_s3_bucket_public_access_block.bucket]
}
