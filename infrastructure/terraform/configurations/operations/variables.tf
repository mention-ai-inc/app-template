variable "account_id" {
  type        = string
  description = "The ID of the AWS account every environment is created in. Feature environments are name-prefixed resources inside it rather than accounts of their own."
}

variable "bucket_name_prefix" {
  type        = string
  description = "Prefix every bucket in the account is named with, including the one holding Terraform's own state. Bucket names are globally unique across all of AWS, so it carries the project's own identity rather than the account number."
}

variable "github_repo" {
  type        = string
  description = "The name of the GitHub repository to connect roles to. Provided in the form `owner/repo`."
}

variable "preferred_region" {
  type        = string
  description = "Region in which to deploy resources. This should be the same for all configurations."
}

variable "domain_name" {
  type        = string
  description = "The domain name of the entire project. The hosted zone is created for it."
}

variable "vpc_cidr_block" {
  type        = string
  description = "The address range of the shared VPC."
}

variable "public_subnet_cidr_blocks" {
  type        = map(string)
  description = "Address range of the public subnet in each availability zone, keyed by zone suffix. The load balancers and the NAT gateway live here."
}

variable "private_subnet_cidr_blocks" {
  type        = map(string)
  description = "Address range of the private subnet in each availability zone, keyed by zone suffix. Tasks, the cache, and anything else without a public address live here."
}

variable "single_nat_gateway" {
  type        = bool
  description = "Whether one NAT gateway serves every private subnet. Cheaper, at the cost of losing egress for every zone when its own zone fails."
  default     = true
}

variable "container_insights" {
  type        = string
  description = "Container Insights setting for the shared ECS cluster. The pools' backlog autoscaling reads the RunningTaskCount metric it publishes."
  default     = "enhanced"
}
