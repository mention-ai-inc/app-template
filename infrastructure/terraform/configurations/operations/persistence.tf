resource "random_password" "redis-auth-token" {
  length  = 48
  special = false
}

resource "aws_secretsmanager_secret" "redis-auth-token" {
  name                    = "REDIS_PASSWORD"
  description             = "Auth token every environment's cache requires of its clients."
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "redis-auth-token" {
  secret_id     = aws_secretsmanager_secret.redis-auth-token.id
  secret_string = random_password.redis-auth-token.result
}

output "redis_auth_token_secret_arn" {
  value = aws_secretsmanager_secret.redis-auth-token.arn
}
