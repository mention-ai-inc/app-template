module "resource-name" {
  source     = "../resource-name"
  full_name  = join("", [var.feature_environment, replace(var.service_name, "_", "-"), "-s-", replace(var.server_name, "_", "-")])
  max_length = 32
}

locals {
  container_definition = merge(
    {
      name      = "app"
      image     = var.image_uri
      essential = true
      portMappings = [{
        containerPort = var.container_port
        protocol      = "tcp"
      }]
      environment = [for key, value in merge(var.env, {
        COMPONENT_TYPE        = "server"
        COMPONENT_NAME        = var.server_name
        PORT                  = tostring(var.container_port)
        CONTAINER_CONCURRENCY = tostring(var.container_concurrency)
        GUNICORN_TIMEOUT      = tostring(var.timeout_seconds)
      }) : { name = key, value = value }]
      secrets = [for key, arn in var.secrets : { name = key, valueFrom = arn }]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.server.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "app"
        }
      }
    },
    var.command == null ? {} : { command = var.command },
  )
}

resource "aws_ecs_task_definition" "server" {
  family                   = module.resource-name.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  task_role_arn            = var.task_role_arn
  execution_role_arn       = var.execution_role_arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = var.cpu_architecture
  }

  container_definitions = jsonencode([local.container_definition])
}
