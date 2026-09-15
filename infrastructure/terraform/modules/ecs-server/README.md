# ECS Server

Deploy a service's REST server as a Fargate service behind the shared application load balancer. The
module owns the task definition, the target group the load balancer routes to, and the autoscaling
that sizes the service. Use it only for servers that take HTTP traffic; queue consumers belong in
`ecs-pool` and one-shot work in `ecs-job`.

Two behaviours differ from the Cloud Run module this mirrors. Fargate has no scale-to-zero, so
`minimum_instances` is floored at one: a server with no running task fails the load balancer's health
check rather than cold-starting on the first request. And the service ignores changes to
`task_definition` and `desired_count`, because `m deploy-<service>` registers a new task definition
revision on each deploy and Terraform would otherwise roll it back.
