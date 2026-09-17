.ONESHELL:
.PHONY: admin
SHELL:=/bin/bash
export PYTHONPATH := $(CURDIR)/tools/mention-template/src:$(PYTHONPATH)


# environment setup
new-project:
	@python3 infrastructure/cli/_helpers/project_setup.py new $(ARGS)
configure-project:
	@python3 infrastructure/cli/_helpers/project_setup.py configure $(ARGS)
doctor:
	@python3 infrastructure/cli/_helpers/project_setup.py doctor $(ARGS)
project-settings:
	@python3 infrastructure/cli/_helpers/project_setup.py settings $(ARGS)
test-project-exports:
	@PROJECT_SETUP_REAL_EXPORTS=1 uv run python -m pytest infrastructure/cli/tests/test_project_exports.py $(ARGS)

test-project-setup:
	@uv run python -m pytest infrastructure/cli/tests $(ARGS)

test-template-launcher:
	@uv run --project tools/mention-template --group dev python -m pytest tools/mention-template/tests $(ARGS)
test-template-release:
	@MENTION_TEMPLATE_ARTIFACTS="$${MENTION_TEMPLATE_ARTIFACTS:-$(CURDIR)/dist/template-release}" uv run --project tools/mention-template --group dev python -m pytest tools/mention-template/tests/test_release_install.py $(ARGS)
build-template-release:
	@uv run --project tools/mention-template python -m mention_template.release --root "$(CURDIR)" $(ARGS)

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
test-provider-%:
	@infrastructure/cli/code-quality/run-pytest library/providers/$* $(ARGS)
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

-include infrastructure/cli/provider/targets.mk
