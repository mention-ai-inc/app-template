output "name" {
  description = "The full name when it fits within the resource's length limit, otherwise the name truncated and suffixed with a digest of the full name."
  value = length(var.full_name) <= var.max_length ? var.full_name : join("", [
    trimsuffix(substr(var.full_name, 0, var.max_length - 8), "-"),
    "-",
    substr(sha1(var.full_name), 0, 7),
  ])
}
