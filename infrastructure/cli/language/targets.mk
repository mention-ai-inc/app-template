test-library:
	@infrastructure/cli/code-quality/run-pytest library $(ARGS)
test-service-%:
	@infrastructure/cli/code-quality/run-pytest services/$* $(ARGS)
test-backfills:
	@infrastructure/cli/code-quality/run-pytest backfills $(ARGS)
