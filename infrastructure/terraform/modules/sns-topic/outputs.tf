output "topic_arn" {
  description = "ARN of the topic, which publishers address and subscriptions attach to."
  value       = aws_sns_topic.topic.arn
}

output "topic_name" {
  description = "Name of the topic."
  value       = aws_sns_topic.topic.name
}
