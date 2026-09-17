# Template launcher releases

The standalone distribution is `mention-template`; `0.1.0b2` was published on September 17, 2026.
It has no runtime dependencies beyond Python 3.11+; uv supplies a compatible Python when
needed. It launches the user's installed `claude` or `codex` interactively. Authentication,
trust prompts, permissions, and conversation history remain owned by that agent.

## Development

The package under `tools/mention-template` owns the shared setup engine. Repository
`m` commands import it from source; generated products do not need the published package.
Keep application dependencies in the root pyproject, not the launcher package.

Use `m test-template-launcher`, `m test-project-setup`, and `m test-project-exports`.
After building, run `m test-template-release` to install the wheel into an isolated
environment and test all six agent/cloud combinations outside a checkout. These tests
substitute release-asset responses and agent executables; they do not authenticate
real agents or access a cloud. Set `MENTION_TEMPLATE_ARTIFACTS` for a nondefault artifact directory.
After agent guidance changes, use `m sync-agent-parity` and `m check-agent-parity`.
Use repository formatting and backend checks before committing. A development wheel
without `templates.json` supports help/resume but reports that creation needs a release build.

## Prepare a beta

1. Choose a new, unpublished version and keep it identical in the package pyproject and `mention_template/__init__.py`.
   Commit shared changes on main and merge that exact commit into all three cloud branches.
2. Run `m build-template-release` from the clean main checkout. Local cloud refs take
   precedence; CI uses fetched origin refs. Each cloud must contain the shared commit
   and differ from it only by additions. A generated product cannot build releases.
3. The output is `dist/template-release`: one wheel, one source distribution,
   `templates.json`, and `aws.tar.gz`, `gcp.tar.gz`, `azure.tar.gz`. The manifest records
   source commits and archive checksums and is bundled into both Python distributions.
   Choose a new destination with `-- --output <directory>` for subsequent builds.
4. Install the built wheel outside the checkout and exercise both agent handoffs.
   Record tested versions, platforms, and outcomes in `docs/setup-verification.md`.

The release builder writes artifacts only. It does not publish, change GitHub visibility,
create tags, deploy cloud resources, or alter existing generated projects. Package source
and MIT license remain in generated products, while the publishing workflow is excluded
from project creation.

## Publish

Before public release, explicitly make the template repository public and configure the
PyPI `mention-template` project or pending Trusted Publisher for GitHub repository
`mention-ai-inc/app-template`, workflow `template-release.yaml`, environment `template-pypi`.
Configure that GitHub environment with required reviewers. Package ownership and environment
protection must be configured by a maintainer before enabling publication.

Dispatch **Template release** from main with `publish=false` first. Review the artifacts
and beta verification record. A separate dispatch with `publish=true` waits for the
protected environment, verifies the repository is public, publishes immutable snapshots
as GitHub prerelease `template-v<version>`, and then publishes Python distributions via
Trusted Publishing. No stored PyPI API token is needed.

If PyPI publication fails after GitHub publication, rerun the publish job with the same
build artifacts. Existing GitHub release assets must match byte-for-byte; they are never
overwritten. A changed build requires a new package version. Do not delete published
snapshots: installed launcher versions continue referring to their exact release URLs.

Public beta does not require completed fresh-account walkthroughs on all three clouds.
It does require honest reporting: agent handoff tests, automated exports, and live cloud
walkthroughs are separate evidence. A healthy endpoint is not proof of sign-in or summarization.
