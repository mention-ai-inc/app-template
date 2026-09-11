FROM python@sha256:1f3781f578e17958f55ada96c0a827bf279a11e10d6a458ecb8bde667afbb669 AS base

ARG UID=1000
ENV UID=${UID}

RUN \
    groupadd -g $UID engineer && \
    useradd -ms /bin/bash engineer --uid $UID --gid $UID && chown engineer:engineer /home/engineer

RUN apt-get update && apt-get install -y curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh

COPY library/pyproject.toml /home/engineer/library/pyproject.toml
COPY library/library/__init__.py /home/engineer/library/library/__init__.py
RUN touch /home/engineer/library/README.md

COPY services/notes/pyproject.toml /home/engineer/services/notes/pyproject.toml
RUN for service in notes; do \
        cd /home/engineer/services/${service} && \
        touch README.md && mkdir ${service}_service && touch ${service}_service/__init__.py; \
    done

COPY admin/pyproject.toml /home/engineer/admin/pyproject.toml
COPY admin/uv.lock /home/engineer/admin/uv.lock
RUN \
    cd /home/engineer/admin && \
    touch README.md && mkdir admin && touch admin/__init__.py && \
    /root/.local/bin/uv sync --frozen

ENV PATH=/home/engineer/.local/bin:/home/engineer/admin/.venv/bin:${PATH}
ENV VIRTUAL_ENV=/home/engineer/admin/.venv

ENV PYTHONWARNINGS="ignore::DeprecationWarning"

COPY --chown=engineer:engineer library/library /home/engineer/admin/.venv/lib/python3.13/site-packages/library
COPY --chown=engineer:engineer services/notes/notes_service /home/engineer/admin/.venv/lib/python3.13/site-packages/notes_service
COPY --chown=engineer:engineer admin/README.md /home/engineer/admin/README.md
COPY --chown=engineer:engineer admin/admin /home/engineer/admin/admin
WORKDIR /home/engineer/admin
RUN mkdir -p admin/data && chown -R engineer:engineer admin/data

ARG FEATURE_ENVIRONMENT=
ENV FEATURE_ENVIRONMENT=${FEATURE_ENVIRONMENT}

USER engineer
