.ONESHELL:
.PHONY: admin
SHELL:=/bin/bash

export PRODUCTION_PROJECT_ID := acme-production-0000
export FEATURE_PROJECT_ID := acme-feature-0000
export OPERATIONS_PROJECT_ID := acme-operations-0000

# environment setup
init:
	@infrastructure/cli/env-setup/init
	@infrastructure/cli/env-setup/create-virtual-environment library
create-venv-%:
	@infrastructure/cli/env-setup/create-virtual-environment $*
update-local-dependencies:
	@infrastructure/cli/env-setup/update-local-dependencies

# code quality
run-checks:
	@infrastructure/cli/code-quality/run-checks
run-checks-backend:
	@infrastructure/cli/code-quality/run-checks-backend
run-checks-frontend:
	@infrastructure/cli/code-quality/run-checks-frontend
run-code-formatting:
	@infrastructure/cli/code-quality/run-code-formatting
scan-vulnerabilities:
	@infrastructure/cli/code-quality/scan-vulnerabilities
run-tests-backend:
	@infrastructure/cli/code-quality/run-tests-backend
test-library:
	@infrastructure/cli/code-quality/run-pytest library $(ARGS)
test-service-%:
	@infrastructure/cli/code-quality/run-pytest services/$* $(ARGS)
test-admin:
	@uv --project admin run pytest admin/tests $(ARGS)

# agentic coding
sync-agent-parity:
	@python3 infrastructure/cli/_helpers/agent_parity.py --sync
check-agent-parity:
	@python3 infrastructure/cli/_helpers/agent_parity.py

# product documentation
sync-prd-links:
	@python3 infrastructure/cli/_helpers/prd_links.py --sync
check-prd-links:
	@python3 infrastructure/cli/_helpers/prd_links.py

# local
build-service-%:
	@infrastructure/cli/local/build-service $*
compile-api:
	@infrastructure/cli/local/compile-api
run-web:
	@infrastructure/cli/local/run-web
run-mobile:
	@infrastructure/cli/local/run-mobile
run-mobile-device-%:
	@infrastructure/cli/local/run-mobile-device $*
admin:
	@infrastructure/cli/local/run-admin $(ARGS)
build-admin:
	@infrastructure/cli/local/build-admin

# deployment
deploy-admin:
	@infrastructure/cli/deployment/deploy-admin
deploy-%:
	@SERVICE=$$(echo $* | awk -F'-' '{print $$1}')
	@NUM_PARTS=$$(echo $* | awk -F'-' '{print NF}')
	@if [ $$NUM_PARTS -ge 3 ]; then
		COMPONENT_TYPE=$$(echo $* | awk -F'-' '{print $$2}')
		COMPONENT_NAME=$$(echo $* | sed 's/^[^-]*-[^-]*-//')
		infrastructure/cli/deployment/deploy $$SERVICE $$COMPONENT_TYPE $$COMPONENT_NAME
	elif [ "$$SERVICE" == "changes" ]; then
		infrastructure/cli/deployment/deploy
	elif [ $$NUM_PARTS -eq 1 ]; then
		infrastructure/cli/deployment/deploy $$SERVICE
	else
		echo "Invalid invocation $*"
		exit 1
	fi
terraform-operations:
	@infrastructure/cli/deployment/run-terraform -f operations -o apply
terraform-services:
	@infrastructure/cli/deployment/run-terraform -f services -o apply
terraform-mcp:
	@infrastructure/cli/deployment/run-terraform -f mcp -o apply
terraform-admin:
	@infrastructure/cli/deployment/run-terraform -f admin -o apply
create-feature-environment:
	@infrastructure/cli/deployment/create-feature-environment
destroy-feature-environment:
	@infrastructure/cli/deployment/destroy-feature-environment
clear-feature-environment:
	@SKIP_CLERK=$(SKIP_CLERK) infrastructure/cli/deployment/run-clear-feature-environment $(ARGS)
list-feature-environments:
	@infrastructure/cli/deployment/list-feature-environments
ensure-feature-environment:
	@infrastructure/cli/deployment/ensure-feature-environment
