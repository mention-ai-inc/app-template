resource "aws_vpc" "shared" {
  cidr_block           = var.vpc_cidr_block
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "shared-vpc" }
}

resource "aws_internet_gateway" "shared" {
  vpc_id = aws_vpc.shared.id

  tags = { Name = "shared-vpc" }
}

resource "aws_subnet" "public" {
  for_each = var.public_subnet_cidr_blocks

  vpc_id                  = aws_vpc.shared.id
  cidr_block              = each.value
  availability_zone       = "${var.preferred_region}${each.key}"
  map_public_ip_on_launch = false

  tags = { Name = "public-${each.key}" }
}

resource "aws_subnet" "private" {
  for_each = var.private_subnet_cidr_blocks

  vpc_id            = aws_vpc.shared.id
  cidr_block        = each.value
  availability_zone = "${var.preferred_region}${each.key}"

  tags = { Name = "private-${each.key}" }
}

resource "aws_eip" "nat" {
  for_each = var.single_nat_gateway ? { for key in slice(sort(keys(var.public_subnet_cidr_blocks)), 0, 1) : key => key } : var.public_subnet_cidr_blocks

  domain = "vpc"

  tags = { Name = "nat-${each.key}" }
}

resource "aws_nat_gateway" "shared" {
  for_each = aws_eip.nat

  allocation_id = each.value.id
  subnet_id     = aws_subnet.public[each.key].id

  tags = { Name = "nat-${each.key}" }

  depends_on = [aws_internet_gateway.shared]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.shared.id

  tags = { Name = "public" }
}

resource "aws_route" "public-internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.shared.id
}

resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  for_each = aws_subnet.private

  vpc_id = aws_vpc.shared.id

  tags = { Name = "private-${each.key}" }
}

resource "aws_route" "private-nat" {
  for_each = aws_subnet.private

  route_table_id         = aws_route_table.private[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.shared[var.single_nat_gateway ? one(keys(aws_nat_gateway.shared)) : each.key].id
}

resource "aws_route_table_association" "private" {
  for_each = aws_subnet.private

  subnet_id      = each.value.id
  route_table_id = aws_route_table.private[each.key].id
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.shared.id
  service_name      = "com.amazonaws.${var.preferred_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [for table in aws_route_table.private : table.id]

  tags = { Name = "s3" }
}

resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id            = aws_vpc.shared.id
  service_name      = "com.amazonaws.${var.preferred_region}.dynamodb"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [for table in aws_route_table.private : table.id]

  tags = { Name = "dynamodb" }
}

output "vpc_id" {
  value = aws_vpc.shared.id
}

output "vpc_cidr_block" {
  value = aws_vpc.shared.cidr_block
}

output "public_subnet_ids" {
  value = [for subnet in aws_subnet.public : subnet.id]
}

output "private_subnet_ids" {
  value = [for subnet in aws_subnet.private : subnet.id]
}
