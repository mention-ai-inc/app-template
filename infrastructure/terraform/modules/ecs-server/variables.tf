variable "region" {
  type        = string
  description = "Region where the service will be deployed. Used when a resource asks for region or location."
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources. Supplied in order to inject it into the environment for containers, so that resources can be correctly accessed in application code."
}

variable "cluster_arn" {
  type        = string
  description = "ARN of the ECS cluster the service runs in."
}

variable "cluster_name" {
  type        = string
  description = "Name of the ECS cluster, which the autoscaling target addresses the service by."
}

variable "service_name" {
  type        = string
  description = "Name of the service the server belongs to."
}

variable "server_name" {
  type        = string
  description = "Name of the server, typically indicating the type of interface it exposes (e.g. rest or grpc)."
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

variable "container_port" {
  type        = number
  description = "Port the server listens on inside the container."
  default     = 8080
}

variable "container_concurrency" {
  type        = number
  description = "Maximum number of concurrent requests a single task is expected to serve. Passed to the server so it can size its own worker pool."
  default     = 80
}

variable "timeout_seconds" {
  type        = number
  description = "Maximum number of seconds a request can take before the request is cancelled."
  default     = 30
}

variable "minimum_instances" {
  type        = number
  description = "Minimum number of tasks to run. Floored at one because Fargate has no scale-to-zero."
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

variable "target_cpu_utilization" {
  type        = number
  description = "Average CPU utilization the autoscaler holds the service at."
  default     = 60
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

variable "health_check_request_path" {
  type        = string
  description = "Path the load balancer polls to decide whether a task is healthy. Defaults to /{server_name}/{service_name}/health."
  default     = null
}

variable "health_check_interval_seconds" {
  type        = number
  description = "Seconds between load balancer health checks."
  default     = 30
}

variable "health_check_timeout_seconds" {
  type        = number
  description = "Seconds a health check may take before it counts as failed."
  default     = 5
}

variable "health_check_healthy_threshold" {
  type        = number
  description = "Consecutive successful health checks before a task is considered healthy."
  default     = 2
}

variable "health_check_unhealthy_threshold" {
  type        = number
  description = "Consecutive failed health checks before a task is considered unhealthy."
  default     = 3
}

variable "deregistration_delay_seconds" {
  type        = number
  description = "Seconds the load balancer keeps draining connections to a removed task."
  default     = 30
}

variable "log_retention_days" {
  type        = number
  description = "Days the container's logs are kept in CloudWatch."
  default     = 30
}

variable "vpc_id" {
  type        = string
  description = "The VPC the service's tasks run in."
}

variable "subnet_ids" {
  type        = list(string)
  description = "The private subnets the service's tasks run in."
}

variable "load_balancer_security_group_id" {
  type        = string
  description = "Security group of the load balancer, which is the only source allowed to reach the container port."
}

variable "target_group_arn" {
  type        = string
  description = "Target group this service registers its tasks into. The load balancer owns it, so the rule routing to it exists before the service does."
}
