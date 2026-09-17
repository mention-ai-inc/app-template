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
