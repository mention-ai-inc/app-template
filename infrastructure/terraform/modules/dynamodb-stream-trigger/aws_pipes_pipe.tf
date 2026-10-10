resource "aws_pipes_pipe" "trigger" {
  name     = module.queue-name.name
  role_arn = aws_iam_role.pipe.arn
  source   = var.table_stream_arn
  target   = aws_sqs_queue.trigger.arn

  source_parameters {
    dynamodb_stream_parameters {
      starting_position                  = "LATEST"
      batch_size                         = var.batch_size
      maximum_batching_window_in_seconds = var.maximum_batching_window_seconds
      maximum_retry_attempts             = var.maximum_retry_attempts
      parallelization_factor             = var.parallelization_factor
      on_partial_batch_item_failure      = "AUTOMATIC_BISECT"

      dead_letter_config {
        arn = aws_sqs_queue.dead-letter.arn
      }
    }

    filter_criteria {
      filter {
        pattern = jsonencode({
          dynamodb = {
            Keys = {
              pk = {
                S = [{ prefix = local.partition_prefix }]
              }
            }
          }
        })
      }
    }
  }

  depends_on = [aws_iam_role_policy.pipe]
}
