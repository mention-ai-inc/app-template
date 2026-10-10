variable "account_id" {
  type        = string
  description = "Identifier of the AWS account every environment lives in. Feature environments are name-prefixed resources inside this account rather than accounts of their own, so both environments resolve to the same value."
}
