export PRODUCTION_ACCOUNT_ID := 000000000000
export FEATURE_ACCOUNT_ID := 000000000000
export OPERATIONS_ACCOUNT_ID := 000000000000
export OPERATIONS_BUCKET_PREFIX := acme-operations-0000
export ECS_CLUSTER_NAME := acme
export AWS_REGION ?= us-east-1

# provider local
build-service-%:
	@infrastructure/cli/provider/deployment/build-service $*
build-admin:
	@infrastructure/cli/provider/deployment/build-admin
list-cache-keys:
	@infrastructure/cli/provider/deployment/list-cache-keys

# deployment
deploy-admin:
	@infrastructure/cli/provider/deployment/deploy-admin
deploy-%:
	@SERVICE=$$(echo $* | awk -F'-' '{print $$1}')
	@NUM_PARTS=$$(echo $* | awk -F'-' '{print NF}')
	@if [ $$NUM_PARTS -ge 3 ]; then
		COMPONENT_TYPE=$$(echo $* | awk -F'-' '{print $$2}')
		COMPONENT_NAME=$$(echo $* | sed 's/^[^-]*-[^-]*-//')
		infrastructure/cli/provider/deployment/deploy $$SERVICE $$COMPONENT_TYPE $$COMPONENT_NAME
	elif [ "$$SERVICE" == "changes" ]; then
		infrastructure/cli/provider/deployment/deploy
	elif [ $$NUM_PARTS -eq 1 ]; then
		infrastructure/cli/provider/deployment/deploy $$SERVICE
	else
		echo "Invalid invocation $*"
		exit 1
	fi
terraform-operations:
	@infrastructure/cli/provider/deployment/run-terraform -f operations -o apply
terraform-services:
	@infrastructure/cli/provider/deployment/run-terraform -f services -o apply
terraform-mcp:
	@infrastructure/cli/provider/deployment/run-terraform -f mcp -o apply
terraform-admin:
	@infrastructure/cli/provider/deployment/run-terraform -f admin -o apply
create-feature-environment:
	@infrastructure/cli/provider/deployment/create-feature-environment
destroy-feature-environment:
	@infrastructure/cli/provider/deployment/destroy-feature-environment
clear-feature-environment:
	@SKIP_CLERK=$(SKIP_CLERK) infrastructure/cli/provider/deployment/run-clear-feature-environment $(ARGS)
list-feature-environments:
	@infrastructure/cli/provider/deployment/list-feature-environments
ensure-feature-environment:
	@infrastructure/cli/provider/deployment/ensure-feature-environment
