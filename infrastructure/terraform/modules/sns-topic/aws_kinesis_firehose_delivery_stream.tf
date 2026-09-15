resource "aws_kinesis_firehose_delivery_stream" "archive" {
  count = local.archive_enabled ? 1 : 0

  name        = local.name
  destination = "extended_s3"

  extended_s3_configuration {
    role_arn            = aws_iam_role.firehose[0].arn
    bucket_arn          = var.archive_bucket_arn
    prefix              = "${local.archive_prefix}publish_date=!{timestamp:yyyy-MM-dd}/"
    error_output_prefix = "${local.archive_prefix}errors/!{firehose:error-output-type}/publish_date=!{timestamp:yyyy-MM-dd}/"
    buffering_interval  = var.buffering_interval_seconds
    buffering_size      = var.buffering_size_mb
    compression_format  = "GZIP"

    cloudwatch_logging_options {
      enabled         = true
      log_group_name  = aws_cloudwatch_log_group.firehose[0].name
      log_stream_name = aws_cloudwatch_log_stream.firehose[0].name
    }
  }
}
