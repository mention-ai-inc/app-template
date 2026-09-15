variable "full_name" {
  type        = string
  description = "The unabbreviated name of the resource, including the feature environment prefix."
}

variable "max_length" {
  type        = number
  description = "The longest name the AWS resource accepts. Target groups allow 32 characters, SQS queues 80, ECS task definition families 255."
  default     = 32
}
