FROM python@sha256:1f3781f578e17958f55ada96c0a827bf279a11e10d6a458ecb8bde667afbb669 AS base

ARG UID=1000
ENV UID=${UID}

RUN \
    groupadd -g $UID engineer && \
    useradd -ms /bin/bash engineer --uid $UID --gid $UID && chown engineer:engineer /home/engineer

RUN apt-get update && apt-get install -y curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh

COPY control-plane/pyproject.toml /home/engineer/control-plane/pyproject.toml
COPY control-plane/uv.lock /home/engineer/control-plane/uv.lock
COPY control-plane/control_plane/__init__.py /home/engineer/control-plane/control_plane/__init__.py
RUN touch /home/engineer/control-plane/README.md

COPY backfills/pyproject.toml /home/engineer/backfills/pyproject.toml
COPY backfills/uv.lock /home/engineer/backfills/uv.lock
RUN \
    cd /home/engineer/backfills && \
    touch README.md && mkdir backfills && touch backfills/__init__.py && \
    /root/.local/bin/uv sync --frozen

COPY control-plane/providers /home/engineer/control-plane/providers
RUN for manifest in /home/engineer/control-plane/providers/*/pyproject.toml; do \
        [ -e "$manifest" ] || continue; \
        /root/.local/bin/uv pip install --python /home/engineer/backfills/.venv "$(dirname "$manifest")"; \
    done

ENV PATH=/home/engineer/.local/bin:/home/engineer/backfills/.venv/bin:${PATH}
ENV VIRTUAL_ENV=/home/engineer/backfills/.venv

ENV PYTHONWARNINGS="ignore::DeprecationWarning"

COPY --chown=engineer:engineer control-plane/control_plane /home/engineer/backfills/.venv/lib/python3.13/site-packages/control_plane
COPY --chown=engineer:engineer backfills/README.md /home/engineer/backfills/README.md
COPY --chown=engineer:engineer backfills/backfills /home/engineer/backfills/backfills
WORKDIR /home/engineer/backfills

ARG FEATURE_ENVIRONMENT=
ENV FEATURE_ENVIRONMENT=${FEATURE_ENVIRONMENT}

USER engineer
CMD ["backfill", "list"]
