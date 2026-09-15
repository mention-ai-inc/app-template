output "name" {
  description = "The full name when it fits within the Container Apps 32-character limit, otherwise the name truncated and suffixed with a digest of the full name."
  value = length(var.full_name) < 33 ? var.full_name : join("", [
    trimsuffix(substr(var.full_name, 0, min(24, length(var.full_name))), "-"),
    "-",
    substr(sha1(var.full_name), 0, 7),
  ])
}
