# GitHub OIDC Role

The AWS counterpart of the workload identity pool. GitHub Actions presents the OIDC token it mints
for a workflow run and receives short-lived credentials for this role; no access key is ever stored
in the repository.

The account holds one OIDC provider for `token.actions.githubusercontent.com`, created in the
operations configuration, and this module creates the roles that trust it. The trust policy pins both
the audience and the repository, so a token minted for another repository cannot assume the role.
