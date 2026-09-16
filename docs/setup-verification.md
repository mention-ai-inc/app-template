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
