output "queue_url" {
  description = "URL of the queue the trigger pool polls for this trigger's records."
  value       = aws_sqs_queue.trigger.url
}

output "queue_name" {
  description = "Name of the queue, which the pool's backlog metric is computed from."
  value       = aws_sqs_queue.trigger.name
}

output "queue_arn" {
  description = "ARN of the queue."
  value       = aws_sqs_queue.trigger.arn
}

output "dead_letter_queue_name" {
  description = "Name of the queue that holds records which exhausted their delivery attempts."
  value       = aws_sqs_queue.dead-letter.name
}
