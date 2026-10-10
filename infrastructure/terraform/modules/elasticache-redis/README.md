# ElastiCache Redis

The GCP estate runs redis-stack on a Compute Engine instance because Memorystore was more expensive
than the workload justified. On AWS the equivalent trade lands the other way: a single-node
ElastiCache replication group with `cache.t4g.micro` costs less than the EC2 instance plus EBS volume
plus the patching it would need, and it comes with encryption, automatic failover, and backups.

The deviation is visible in one place: redis-stack modules (RedisJSON, RediSearch) are not available
on ElastiCache. Anything relying on them must use OSS Redis data structures instead, or move to
MemoryDB.
