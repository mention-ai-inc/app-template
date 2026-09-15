resource "aws_ecs_cluster" "shared" {
  name = "acme"

  setting {
    name  = "containerInsights"
    value = var.container_insights
  }
}

resource "aws_ecs_cluster_capacity_providers" "shared" {
  cluster_name       = aws_ecs_cluster.shared.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 1
  }
}

output "ecs_cluster_arn" {
  value = aws_ecs_cluster.shared.arn
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.shared.name
}
