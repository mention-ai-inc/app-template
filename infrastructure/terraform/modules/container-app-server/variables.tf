variable "resource_group_name" {
  type        = string
  description = "Name of the resource group the Container App belongs to."
}

variable "location" {
  type        = string
  description = "Region the Container App is deployed to. Used when a resource asks for region or location."
}

variable "container_app_environment_id" {
  type        = string
  description = "Resource ID of the Container App Environment that hosts the app."
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources. Supplied in order to inject it into the environment for Container Apps, so that resources can be correctly accessed in application code."
}

variable "service_name" {
  type        = string
  description = "Name of the service the server belongs to."
}

variable "server_name" {
  type        = string
  description = "Name of the server, typically indicating the type of service (e.g. rest or grpc)."
}

variable "identity_id" {
  type        = string
  description = "Resource ID of the user-assigned managed identity the app runs as, pulls images as, and reads Key Vault secrets as."
}

variable "registry_login_server" {
  type        = string
  description = "Login server of the container registry the image is pulled from."
}

variable "image" {
  type        = string
  description = "Fully qualified container image to deploy. The default is a placeholder that lets the app be created before the first image is pushed; thereafter the deployment scripts own the image and Terraform ignores changes to it."
  default     = "mcr.microsoft.com/k8se/quickstart:latest"
}

variable "command" {
  type        = list(string)
  description = "The command to pass to the container."
  default     = null
}

variable "container_concurrency" {
  type        = number
  description = "Number of concurrent requests per replica before the HTTP scale rule adds another."
  default     = 80
}

variable "timeout_seconds" {
  type        = number
  description = "Maximum number of seconds a request can take before the application cancels it. Container Apps has no request timeout of its own, so this is applied by the server process."
  default     = 60
}

variable "minimum_instances" {
  type        = number
  description = "Minimum number of replicas to run."
  default     = 0
}

variable "maximum_instances" {
  type        = number
  description = "Maximum number of replicas to run."
  default     = 10
}

variable "cpu" {
  type        = number
  description = "Number of vCPUs to allocate to each replica. Container Apps requires memory to be exactly twice this value in gibibytes."
  default     = 0.5
}

variable "memory" {
  type        = string
  description = "Amount of memory to allocate to each replica, as a Kubernetes quantity such as 1Gi."
  default     = "1Gi"
}

variable "target_port" {
  type        = number
  description = "Port the container listens on."
  default     = 8080
}

variable "env" {
  type        = map(string)
  description = "Environment variables to set in the container."
  default     = {}
}

variable "secret_env" {
  type        = map(string)
  description = "Environment variables whose values are read from Key Vault at runtime, as a map of variable name to versionless Key Vault secret URI. Values never enter Terraform state."
  default     = {}
}

variable "external_enabled" {
  type        = bool
  description = "Whether the managed ingress accepts traffic from outside the Container App Environment."
  default     = true
}

variable "ip_allowlist" {
  type = list(object({
    name             = string
    ip_address_range = string
  }))
  description = "CIDR ranges permitted to reach the ingress. An empty list permits every caller."
  default     = []
}

variable "health_check_request_path" {
  type        = string
  description = "Path the readiness and liveness probes request. Defaults to /{server_name}/{service_name}/health."
  default     = null
}

variable "custom_domain_fqdn" {
  type        = string
  description = "Fully qualified hostname to bind to the app with a managed certificate. Leave empty to serve only on the environment's default domain."
  default     = ""
}

variable "dns_record_name" {
  type        = string
  description = "Record name within the DNS zone for the custom domain, relative to the zone apex."
  default     = ""
}

variable "dns_zone_name" {
  type        = string
  description = "Name of the Azure DNS zone that holds the custom domain's records."
  default     = ""
}

variable "dns_zone_resource_group_name" {
  type        = string
  description = "Name of the resource group that holds the DNS zone."
  default     = ""
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to the Container App."
  default     = {}
}
