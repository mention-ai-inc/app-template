variable "region" {
  type        = string
  description = "Region where the pool will be deployed."
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources."
}

variable "cluster_arn" {
  type        = string
  description = "ARN of the ECS cluster the pool runs in."
}

variable "cluster_name" {
  type        = string
  description = "Name of the ECS cluster, which the autoscaling target addresses the pool by."
}

variable "service_name" {
  type        = string
  description = "Name of the service whose entrypoints the pool hosts."
}

variable "pool_name" {
  type        = string
  description = "Name of the pool, which distinguishes it from the other pools of the same service and appears in its ECS name."
}

variable "component_type" {
  type        = string
  description = "The kind of entrypoint the pool hosts. Every entrypoint in one pool is of the same kind, so this stays a per-process constant."

  validation {
    condition     = contains(["executor", "listener", "trigger"], var.component_type)
    error_message = "A pool hosts executors, listeners, or triggers."
  }
}

variable "task_role_arn" {
  type        = string
  description = "ARN of the IAM role the container's own AWS calls are made as."
}

variable "execution_role_arn" {
  type        = string
  description = "ARN of the IAM role the ECS agent pulls images and reads secrets as."
}

variable "image_uri" {
  type        = string
  description = "URI of the container image to deploy."
  default     = "public.ecr.aws/docker/library/busybox:stable"
}

variable "command" {
  type        = list(string)
  description = "The command to pass to the container."
  default     = null
}

variable "container_concurrency" {
  type        = number
  description = "Maximum number of messages a single task processes at once."
  default     = 80
}

variable "timeout_seconds" {
  type        = number
  description = "Maximum number of seconds a single message may take before its handler is cancelled."
  default     = 60
}

variable "minimum_instances" {
  type        = number
  description = "Minimum number of tasks to run. Floored at one because a pool that is not running consumes nothing."
  default     = 1
}

variable "maximum_instances" {
  type        = number
  description = "Maximum number of tasks to run."
  default     = 10
}

variable "cpu" {
  type        = string
  description = "CPU units to allocate to each task, as a string. 1024 units is one vCPU."
  default     = "512"
}

variable "memory" {
  type        = string
  description = "Memory to allocate to each task, in MiB, as a string."
  default     = "1024"
}

variable "cpu_architecture" {
  type        = string
  description = "CPU architecture of the task's runtime platform."
  default     = "ARM64"
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

variable "backlog_queue_names" {
  type        = list(string)
  description = "Names of the queues the pool consumes. Their combined depth is the metric the autoscaler sizes the pool on."
  default     = []
}

variable "target_messages_per_task" {
  type        = number
  description = "Number of waiting messages per running task the autoscaler holds the pool at."
  default     = 100
}

variable "scale_in_cooldown_seconds" {
  type        = number
  description = "Seconds the autoscaler waits after a scale-in before scaling in again."
  default     = 300
}

variable "scale_out_cooldown_seconds" {
  type        = number
  description = "Seconds the autoscaler waits after a scale-out before scaling out again."
  default     = 60
}

variable "log_retention_days" {
  type        = number
  description = "Days the container's logs are kept in CloudWatch."
  default     = 30
}

variable "vpc_id" {
  type        = string
  description = "The VPC the pool's tasks run in."
}

variable "subnet_ids" {
  type        = list(string)
  description = "The private subnets the pool's tasks run in."
}
