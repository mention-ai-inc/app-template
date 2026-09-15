variable "region" {
  description = "The region in which the job runs."
  type        = string
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources."
}

variable "cluster_arn" {
  description = "ARN of the ECS cluster the job's tasks run in."
  type        = string
}

variable "service_name" {
  description = "The name of the service the job belongs to."
  type        = string
}

variable "job_name" {
  description = "The name of the job."
  type        = string
}

variable "task_count" {
  description = "The number of tasks a scheduled run starts."
  type        = number
  default     = 1
}

variable "max_retries" {
  description = "The number of times a scheduled run is retried after a failure."
  type        = number
  default     = 0
}

variable "task_timeout_seconds" {
  description = "The maximum time a task is allowed to run before the scheduler stops it."
  type        = number
  default     = 600
}

variable "task_role_arn" {
  description = "ARN of the IAM role the container's own AWS calls are made as."
  type        = string
}

variable "execution_role_arn" {
  description = "ARN of the IAM role the ECS agent pulls images and reads secrets as."
  type        = string
}

variable "image_uri" {
  description = "The container image the job runs."
  type        = string
  default     = "public.ecr.aws/docker/library/busybox:stable"
}

variable "command" {
  type        = list(string)
  description = "The command to pass to the container."
  default     = null
}

variable "env" {
  type        = map(string)
  description = "Environment variables to set in the container."
  default     = {}
}

variable "secrets" {
  type        = map(string)
  description = "Environment variables whose values are read from Secrets Manager at task start, keyed by variable name and valued by secret ARN."
  default     = {}
}

variable "cpu" {
  type        = string
  description = "CPU units to allocate to each task, as a string. 1024 units is one vCPU."
  default     = "1024"
}

variable "memory" {
  type        = string
  description = "Memory to allocate to each task, in MiB, as a string."
  default     = "2048"
}

variable "cpu_architecture" {
  type        = string
  description = "CPU architecture of the task's runtime platform."
  default     = "ARM64"
}

variable "log_retention_days" {
  type        = number
  description = "Days the container's logs are kept in CloudWatch."
  default     = 30
}

variable "vpc_id" {
  type        = string
  description = "The VPC the job's tasks run in."
}

variable "subnet_ids" {
  type        = list(string)
  description = "The private subnets the job's tasks run in."
}

variable "schedule" {
  description = "EventBridge Scheduler expression that runs the job, such as cron(0 3 * * ? *). Empty for jobs that are only ever run on demand."
  type        = string
  default     = ""
}
