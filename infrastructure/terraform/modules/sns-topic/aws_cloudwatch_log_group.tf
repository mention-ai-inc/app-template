resource "aws_cloudwatch_log_group" "firehose" {
  count = local.archive_enabled ? 1 : 0

  name              = "/aws/kinesisfirehose/${local.name}"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_stream" "firehose" {
  count = local.archive_enabled ? 1 : 0

  name           = "s3-delivery"
  log_group_name = aws_cloudwatch_log_group.firehose[0].name
}
