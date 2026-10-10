## After changing `control-plane/`, `library/`, or a provider, re-sync the local dependencies before running anything

The shared Python packages are **not** editable installs in the packages that depend on them. Each dependant declares a path dependency, and `uv` installs a **built copy** into that package's `.venv`:

| Package | Installed as built copies into its `.venv` |
| --- | --- |
| `admin` | `control-plane`, every `control-plane/providers/<cloud>` |
| `control-plane/providers/<cloud>` | `control-plane` |
| `library` (Python backend) | `control-plane` |
| `services/*` (Python backend) | `control-plane`, `library`, every provider |
| `backfills` (Python backend) | `control-plane`, every provider |

Editing `control-plane/control_plane/**`, `library/library/**`, or `control-plane/providers/<cloud>/control_plane_provider_<cloud>/**` changes nothing inside a dependant's `.venv/lib/python3.13/site-packages/` until you re-sync.

This is the repository's most reliable way to get a wrong answer, because **every symptom looks like a real result**:

- `uv run pytest` inside a service passes — against the *old* kernel. A green service suite is not evidence that your `control-plane` or `library` change works.
- Pyright reports `"<new_symbol>" is unknown import symbol` for something you can see in the source, in a file that is obviously correct.
- A script or REPL check exercises the pre-change behaviour and "confirms" the bug you already fixed.

None of these announce themselves as staleness. Treat a result that contradicts the source as a sync problem before you treat it as a code problem.

### What to run

After any change under `control-plane/`, `library/`, or a provider package — before service tests, before `m run-checks-*`, before any manual verification:

```
m update-local-dependencies
```

That is the only command you should reach for in normal work. It copies `control-plane/control_plane` into `admin` and every provider venv, then hands over to the language slot (`infrastructure/cli/language/update-local-dependencies`), which copies `control-plane/control_plane` into `library`, `services/*` and `backfills`, `library/library` into `services/*`, and each provider package into `services/*` and `backfills`. It is fast and safe to run whenever you are unsure. Per-package escape hatch, when you are chasing one venv specifically:

```
cd services/notes && uv sync --reinstall-package library --reinstall-package control-plane
```

### Confirming a venv is current

When a check fails in a way that contradicts the source, verify the installed copy rather than re-reading your own diff:

```
grep -c '<new-symbol>' services/*/.venv/lib/python*/site-packages/control_plane/<path>.py \
                       admin/.venv/lib/python*/site-packages/control_plane/<path>.py
```

A `0` against a symbol that exists in `control-plane/control_plane/<path>.py` means the venv is stale, not that the code is wrong. The same check works for `library/<path>.py` in a service venv.

### The same trap in reverse

A cloud provider distribution under `control-plane/providers/<cloud>/` depends on `control-plane` and is itself a built copy inside `admin`, `services/*` and `backfills`. Changing a provider and then running another package's tests has the identical failure mode, and the identical fix — `m update-local-dependencies` re-copies those as well.

Deployed images are unaffected — they build from the repository, not from a developer `.venv`. This is strictly a local-development hazard, which is part of why it keeps recurring: CI is green, so nothing external corrects you. A TypeScript backend links its workspace packages in place and has no equivalent hazard; the Python control plane and providers keep it on every branch.
