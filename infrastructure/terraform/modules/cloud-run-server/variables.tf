# admin
variable "project_id" {
  type        = string
  description = "ID of the GCP project the service belongs to."
}

variable "region" {
  type        = string
  description = "Region where the service will be deployed. Used when a resource asks for region or location."
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources. Supplied in order to inject it into the environment for Cloud Run services, so that resources can be correctly accessed in application code."
}

# cloud run configuration
variable "service_name" {
  type        = string
  description = "Name of the Cloud Run service."
}

variable "server_name" {
  type        = string
  description = "Name of the server, typically indicating the type of service (e.g. rest or grpc)."
}

variable "service_account_email" {
  type        = string
  description = "Email address of the service account to associate with the service."
}

variable "image_uri" {
  type        = string
  description = "URI of the container image to deploy."
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "command" {
  type        = list(string)
  description = "The command to pass to the container."
  default     = null
}

variable "container_concurrency" {
  type        = number
  description = "Maximum number of concurrent requests allowed for a container."
  default     = 80
}

variable "timeout_seconds" {
  type        = number
  description = "Maximum number of seconds a request can take before the request is cancelled."
  default     = 60
}

variable "minimum_instances" {
  type        = number
  description = "Minimum number of container instances to run."
  default     = 0
}

variable "maximum_instances" {
  type        = number
  description = "Maximum number of container instances to run."
  default     = 10
}

variable "cpu" {
  type        = string
  description = "Number of vCPUs to allocate to the service, as a string."
  default     = "1"
}

variable "memory" {
  type        = string
  description = "Amount of memory to allocate to the service, in MB. For example, 256Mi = 256 MB."
  default     = "512Mi"
}

variable "env" {
  type        = map(string)
  description = "Environment variables to set in the container."
  default     = {}
}

# access control
variable "ingress" {
  type        = string
  description = "Ingress setting for the Cloud Run service. Set to INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER to make the service unreachable at its run.app URL."
  default     = "INGRESS_TRAFFIC_ALL"
}

variable "public_access" {
  type        = bool
  description = "Whether any caller may invoke the service unauthenticated. When false, only the IAP service agent is granted the invoker role, which requires project_number."
  default     = true
}

variable "project_number" {
  type        = string
  description = "Number of the GCP project the service belongs to. Required when public_access is false."
  default     = null
}

variable "iap_enabled" {
  type        = bool
  description = "Whether to enable Identity-Aware Proxy on the backend service."
  default     = false
}

variable "security_policy" {
  type        = string
  description = "Self link of a Cloud Armor security policy to attach to the backend service."
  default     = null
}

variable "keep_alive_enabled" {
  type        = bool
  description = "Whether to create the scheduler job that pings the health endpoint. Disable for services whose run.app URL rejects unauthenticated requests."
  default     = true
}

# backend service configuration
variable "backend_service_session_affinity" {
  type        = string
  description = "Session affinity to use for the backend service."
  default     = "NONE"
}

variable "backend_service_timeout_seconds" {
  type        = number
  description = "Timeout for requests to the backend service, in seconds."
  default     = 30
}

variable "backend_service_protocol" {
  type        = string
  description = "Denotes HTTP or HTTPS for the backend service."
  default     = "HTTPS"
}

variable "backend_service_load_balancing_scheme" {
  type        = string
  description = "Denotes internal or external load balancing for the backend service. Note that this must be the same as the load balancing scheme for the forwarding rule of any load balancer this backend service is connected to."
  default     = "EXTERNAL_MANAGED"
}

variable "backend_service_balancing_mode" {
  type        = string
  description = "Denotes whether the backend service is global or regional."
  default     = "UTILIZATION"
}

variable "backend_service_name_suffix" {
  type        = string
  description = "Optional suffix appended to the backend service name. Occasionally needed to fix stuck GCP resources."
  default     = ""
}

# health check configuration
variable "health_check_request_path" {
  type        = string
  description = "Path to use when checking the health of the service. Defaults to /{server_name}/{service_name}/health."
  default     = null
}

variable "health_check_port" {
  type        = number
  description = "Port to use when checking the health of the service."
  default     = 443
}

variable "health_check_timeout_seconds" {
  type        = number
  description = "Timeout for health checks, in seconds."
  default     = 5
}

variable "health_check_check_interval_seconds" {
  type        = number
  description = "Interval between health checks, in seconds."
  default     = 5
}

variable "health_check_healthy_threshold" {
  type        = number
  description = "Number of consecutive successful health checks before a backend is considered healthy."
  default     = 1
}

variable "health_check_unhealthy_threshold" {
  type        = number
  description = "Number of consecutive failed health checks before a backend is considered unhealthy."
  default     = 3
}

# networking
variable "vpc_network" {
  type        = string
  description = "The ID of the VPC network to deploy the service to."
}

variable "vpc_subnetwork" {
  type        = string
  description = "The ID of the VPC subnet to deploy the service to."
}

# scheduler
variable "health_check_interval_minutes" {
  type        = number
  description = "Interval between health checks, in minutes."
  default     = 5
}
