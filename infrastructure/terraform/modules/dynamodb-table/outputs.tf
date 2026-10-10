output "table_name" {
  description = "Name of the table."
  value       = aws_dynamodb_table.table.name
}

output "table_arn" {
  description = "ARN of the table."
  value       = aws_dynamodb_table.table.arn
}

output "stream_arn" {
  description = "ARN of the table's change stream, which the triggers read."
  value       = aws_dynamodb_table.table.stream_arn
}

output "collection_index_name" {
  description = "Name of the index that serves collection reads."
  value       = one([for index in aws_dynamodb_table.table.global_secondary_index : index.name])
}
