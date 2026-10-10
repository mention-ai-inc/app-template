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

COPY admin/pyproject.toml /home/engineer/admin/pyproject.toml
COPY admin/uv.lock /home/engineer/admin/uv.lock
RUN \
    cd /home/engineer/admin && \
    touch README.md && mkdir admin && touch admin/__init__.py && \
    /root/.local/bin/uv sync --frozen

COPY control-plane/providers /home/engineer/control-plane/providers
RUN for manifest in /home/engineer/control-plane/providers/*/pyproject.toml; do \
        [ -e "$manifest" ] || continue; \
        /root/.local/bin/uv pip install --python /home/engineer/admin/.venv "$(dirname "$manifest")"; \
    done

ENV PATH=/home/engineer/.local/bin:/home/engineer/admin/.venv/bin:${PATH}
ENV VIRTUAL_ENV=/home/engineer/admin/.venv

ENV PYTHONWARNINGS="ignore::DeprecationWarning"

COPY --chown=engineer:engineer control-plane/control_plane /home/engineer/admin/.venv/lib/python3.13/site-packages/control_plane
COPY --chown=engineer:engineer admin/README.md /home/engineer/admin/README.md
COPY --chown=engineer:engineer admin/admin /home/engineer/admin/admin
WORKDIR /home/engineer/admin
RUN mkdir -p admin/data && chown -R engineer:engineer admin/data

ARG FEATURE_ENVIRONMENT=
ENV FEATURE_ENVIRONMENT=${FEATURE_ENVIRONMENT}

USER engineer
