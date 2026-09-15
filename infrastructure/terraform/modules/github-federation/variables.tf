variable "display_name" {
  type        = string
  description = "Display name of the Entra ID application registration."
}

variable "description" {
  type        = string
  description = "Human-friendly description of what the federated identity is used for."
}

variable "issuer" {
  type        = string
  description = "The OIDC issuer that mints the tokens exchanged for Entra ID tokens."
  default     = "https://token.actions.githubusercontent.com"
}

variable "subjects" {
  type        = list(string)
  description = "Subject claims accepted from the issuer, such as repo:owner/repo:ref:refs/heads/main. Entra ID matches these exactly, so one credential is needed per branch, tag, environment, or pull-request trigger."
}

variable "role_assignments" {
  type = map(object({
    role  = string
    scope = string
  }))
  description = "Built-in role definitions to grant to the application's service principal, each at the scope it applies to. Keys are static names, because a scope is not known until the resource it names exists."
  default     = {}
}

variable "owner_object_ids" {
  type        = list(string)
  description = "Object IDs of the directory principals that own the application and its service principal."
  default     = []
}
