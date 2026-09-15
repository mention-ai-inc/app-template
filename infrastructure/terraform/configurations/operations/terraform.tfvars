account_id         = "000000000000"
bucket_name_prefix = "acme-operations-0000"
github_repo        = "mention-ai-inc/app-template"
preferred_region   = "us-east-1"
domain_name        = "acme.example.com"

vpc_cidr_block = "10.0.0.0/16"

public_subnet_cidr_blocks = {
  a = "10.0.0.0/20"
  b = "10.0.16.0/20"
  c = "10.0.32.0/20"
}

private_subnet_cidr_blocks = {
  a = "10.0.128.0/20"
  b = "10.0.144.0/20"
  c = "10.0.160.0/20"
}

single_nat_gateway = true
container_insights = "enhanced"
