# ECS Pool

A pool is one Fargate service hosting every entrypoint of one kind for one service: all of its
executors, all of its listeners, or all of its triggers. On GCP a pool is an HTTP server and Pub/Sub,
Cloud Tasks, and Eventarc push into it. On AWS nothing pushes: the pool long-polls the SQS queues its
entrypoints own, and the queue URLs reach it as environment variables.

That reverses the scaling story. A Cloud Run pool scales from zero on the first push; a Fargate pool
must already be running to see a message at all, so `minimum_instances` is floored at one and the
autoscaler sizes the pool on queue backlog rather than CPU.
