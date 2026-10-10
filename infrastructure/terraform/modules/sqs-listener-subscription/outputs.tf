output "queue_urls" {
  description = "URLs of the listener's queues, which the listener pool polls."
  value       = [for queue in aws_sqs_queue.listener : queue.url]
}

output "queue_names" {
  description = "Names of the listener's queues, which the pool's backlog metric is computed from."
  value       = [for queue in aws_sqs_queue.listener : queue.name]
}

output "queue_arns" {
  description = "ARNs of the listener's queues."
  value       = [for queue in aws_sqs_queue.listener : queue.arn]
}

output "dead_letter_queue_name" {
  description = "Name of the queue that holds events which exhausted their delivery attempts."
  value       = aws_sqs_queue.dead-letter.name
}

output "dead_letter_queue_url" {
  description = "URL of the dead-letter queue, which the listener drains on demand."
  value       = aws_sqs_queue.dead-letter.url
}
