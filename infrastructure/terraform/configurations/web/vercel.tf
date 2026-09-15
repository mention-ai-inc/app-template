data "vercel_project_directory" "web-app" {
  path = "../../../.."
}

data "aws_secretsmanager_secret_version" "clerk-secret-key" {
  secret_id = "CLERK_SECRET_KEY"
}

resource "vercel_project" "web-app" {
  name            = "${local.feature_environment}acme-web"
  team_id         = var.vercel_team_id
  framework       = var.frontend_framework
  ignore_command  = "exit 0"
  install_command = "pnpm install"
  build_command   = "pnpm build"
  root_directory  = "apps/web"

  resource_config = {
    function_default_timeout = var.function_default_timeout
  }

  environment = [
    {
      key    = "CLERK_SECRET_KEY"
      target = ["production"]
      value  = data.aws_secretsmanager_secret_version.clerk-secret-key.secret_string
    },
    {
      key    = "VITE_CLERK_PUBLISHABLE_KEY"
      target = ["production"]
      value  = module.environment.settings.tokens.clerk_publishable_key
    },
    {
      key    = "VITE_FEATURE_ENVIRONMENT"
      target = ["production"]
      value  = local.feature_environment
    }
  ]
}

resource "vercel_project_domain" "web-app" {
  project_id = vercel_project.web-app.id
  team_id    = var.vercel_team_id
  domain     = "${local.feature_environment}${var.app_domain}"
}

resource "vercel_deployment" "web-app" {
  project_id  = vercel_project.web-app.id
  team_id     = var.vercel_team_id
  files       = data.vercel_project_directory.web-app.files
  path_prefix = data.vercel_project_directory.web-app.path
  production  = true

  project_settings = {
    output_directory = "dist"
  }
}
