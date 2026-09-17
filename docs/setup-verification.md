# Setup verification

Fresh-account onboarding is **unverified** until a walkthrough is recorded for a specific cloud and revision. Automated tests validate generation and configuration; they do not prove a live cloud deployment.

## Automated verification — September 16, 2026

Tested on macOS against shared revision `ead7331`, with cloud snapshots `fdabec8` (GCP), `efda600` (AWS), and `b123ee8` (Azure).

- Setup tests: 36 passed. The separate real-snapshot suite passed all 12 tests, including minimal deployment sequencing, deployment failure propagation, and health-check timeouts using stubbed cloud operations.
- Exported each cloud into a fresh repository and ran the full configure-project apply, including dependency installation and API-client generation. A second preview reported zero changes for all three.
- Local doctor, agent guidance parity, and frontend/backend checks passed in all three generated projects after repository formatting.
- Terraform initialized with backends disabled and validated all five configurations on each cloud, for 15 successful validations.
- Authentication configuration tests: 4 passed.

Generated projects used the default web-only profile with monitoring disabled; Terraform validation covered every surface. No cloud resources were provisioned. Cloud permissions, DNS, CI credentials, sign-in, summarization, persistence, and live cleanup still need a fresh-account walkthrough.

## Recording a live walkthrough

After testing, record the source revision, cloud, date, local platform, which surfaces were enabled, whether the published instructions alone were sufficient, and the results of sign-in, organization creation, note creation, summarization, persistence, and cleanup. Record blockers and manual workarounds explicitly. Never record credentials here.

## Standalone launcher beta — September 17, 2026 (UTC)

Launcher implementation `823949f`, package `0.1.0b1`, tested on macOS:

- All 25 launcher tests passed on Python 3.11 and 3.13. Terminal tests cover both agent adapters, exit codes, interruption, and resume with unchanged configuration.
- All 36 setup tests and 12 real-cloud-snapshot tests passed after moving the engine into the package.
- Built the wheel, source distribution, and three pinned cloud archives with `m build-template-release`. All 8 installed-distribution tests passed outside the checkout, covering all six agent/cloud combinations. Download responses and agent executables are substituted in these tests; archive checksums and actual project initialization still run.
- Full repository checks and agent parity passed. An AWS-generated project completed real dependency installation and API generation through configure-project; its next preview reported zero changes and local doctor passed.
- The installed wheel opened Claude Code `2.1.274` and Codex CLI `0.154.0` in their respective generated projects and displayed their native trust prompts. Both sessions were exited at those prompts. This verifies interactive handoff, not authenticated agent conversation or live onboarding.

At the time of these local checks, the package and snapshots were unpublished and the
macOS/Linux CI matrices had not run on GitHub. The publication checks below supersede
that status. Authenticated guided conversations, fresh-account cloud walkthroughs, and
live cleanup remain unverified.

## Public beta publication — September 17, 2026

Published `mention-template==0.1.0b1` through GitHub Actions run `35167363080`, from shared
revision `44d629f`. Release build and installed-distribution checks passed on both Linux
and macOS. The three snapshot archives are public in GitHub release `template-v0.1.0b1`.

An uncached `uvx mention-template --version` resolved the package from PyPI and returned
`0.1.0b1`. A separate invocation of exactly `uvx mention-template` from an empty temporary
directory completed the interactive choices, downloaded the public AWS snapshot, created
an independent project, and opened Claude Code at its native trust prompt. No local wheel,
template checkout, mocked download, or GitHub authentication was needed. The session was
exited at the trust prompt; authenticated onboarding and live cloud deployment remain unverified.

## GCP onboarding corrections and next beta candidate — September 17, 2026

The Racetrac GCP walkthrough exposed inverted feature/production project-number placeholders.
A signed-in user created a note; after correcting routing and deploying that fix, normal command
redispatch generated and persisted its summary. Browser reload confirmation and actual Sentry/Logfire
delivery remain unverified. This evidence applies to GCP; it does not establish live AWS/Azure onboarding.

The corrected source is covered by distinct-number export/regeneration tests and task URL checks.
Onboarding now includes resumable foundation provisioning, semantic identity checks, Clerk/Vercel
verification, pinned cache-image preparation, and metadata-only summary diagnosis and recovery.
Merge-triggered demo deployment remains enabled by default, with an explicit pause and manual
environment selection. New forks receive a compact verification checkpoint instead of this release log.

The `0.1.0b2` candidate was validated locally before the publication recorded below. Validation uses isolated generated repositories and
stubbed external services; it does not provision or deploy resources. Run the setup, export, GCP
onboarding/provider, launcher, and installed-release suites before publishing. The provider suite
uses `GOOGLE_CLOUD_PROJECT=example-feature` to avoid querying runtime metadata during collection.


## Published 0.1.0b2 — September 17, 2026

Published the approved candidate from main revision `cff5ac004dc051e55c55a4c5e6d5a4e339baf550`.
The manifest pins GCP `72f29d9`, AWS `543931d`, and Azure `4100143`.
Validation workflow run `35281917405` passed Linux and macOS checks. Publication workflow run
`35282090500` repeated those checks and published GitHub prerelease `template-v0.1.0b2` and
PyPI `mention-template==0.1.0b2` through the configured release environment.

The publication manifest and cloud archive digests matched the successful validation run.
All six downloaded GitHub release files matched the approved build byte-for-byte; PyPI wheel
and source-distribution hashes matched too. Installation from the public PyPI index outside
this checkout returned `mention-template 0.1.0b2`. The first immediate default-index resolution
had not found the new version; a refreshed request to the public index succeeded.

This publication did not deploy Racetrac or change cloud infrastructure. Prior live-walkthrough
limitations, including browser reload confirmation and monitoring delivery, remain unchanged.
