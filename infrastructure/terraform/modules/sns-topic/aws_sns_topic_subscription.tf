resource "aws_sns_topic_subscription" "archive" {
  count = local.archive_enabled ? 1 : 0

  topic_arn             = aws_sns_topic.topic.arn
  protocol              = "firehose"
  endpoint              = aws_kinesis_firehose_delivery_stream.archive[0].arn
  subscription_role_arn = aws_iam_role.sns-delivery[0].arn
  raw_message_delivery  = false
}
