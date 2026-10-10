output "queue_name" {
  description = "The short name of the queue created for this command."
  value       = aws_sqs_queue.queue.name
}

output "queue_url" {
  description = "The URL the dispatcher sends commands to and the executor pool reads them from."
  value       = aws_sqs_queue.queue.url
}

output "queue_arn" {
  description = "ARN of the queue."
  value       = aws_sqs_queue.queue.arn
}

output "dead_letter_queue_name" {
  description = "The short name of the queue that holds commands which exhausted their attempts."
  value       = aws_sqs_queue.dead-letter.name
}

output "dead_letter_queue_url" {
  description = "The URL of the dead-letter queue."
  value       = aws_sqs_queue.dead-letter.url
}

output "task_concurrency" {
  description = "The concurrency the executor pool should read this queue at."
  value       = var.task_concurrency
}
