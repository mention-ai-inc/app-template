# python 3.13 slim
FROM python@sha256:1f3781f578e17958f55ada96c0a827bf279a11e10d6a458ecb8bde667afbb669 AS base

ARG SERVICE
ENV SERVICE=${SERVICE}
ARG UID=1000
ENV UID=${UID}

# make user
RUN \
    groupadd -g $UID engineer && \
    useradd -ms /bin/bash engineer --uid $UID --gid $UID && chown engineer:engineer /home/engineer

# install uv
RUN apt-get update && apt-get install -y curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh

# empty library so that it's acceptably installed as a dependency, but changes come after expensive uv sync
COPY library/pyproject.toml /home/engineer/library/pyproject.toml
COPY library/library/__init__.py /home/engineer/library/library/__init__.py
RUN touch /home/engineer/library/README.md

# install dependencies
COPY services/${SERVICE}/pyproject.toml /home/engineer/services/${SERVICE}/pyproject.toml
COPY services/${SERVICE}/uv.lock /home/engineer/services/${SERVICE}/uv.lock
RUN \
    cd /home/engineer/services/${SERVICE} && \
    touch README.md && mkdir ${SERVICE}_service && touch ${SERVICE}_service/__init__.py && \
    /root/.local/bin/uv sync --frozen

COPY library/providers /home/engineer/library/providers
RUN for manifest in /home/engineer/library/providers/*/pyproject.toml; do \
        [ -e "$manifest" ] || continue; \
        /root/.local/bin/uv pip install \
            --python /home/engineer/services/${SERVICE}/.venv "$(dirname "$manifest")"; \
    done

ENV PATH=/home/engineer/.local/bin:/home/engineer/services/${SERVICE}/.venv/bin:${PATH}
ENV VIRTUAL_ENV=/home/engineer/services/${SERVICE}/.venv

# environment settings
ENV PYTHONWARNINGS="ignore::DeprecationWarning"

# add code for component
COPY --chown=engineer:engineer services/${SERVICE}/README.md /home/engineer/services/${SERVICE}/README.md
COPY --chown=engineer:engineer services/${SERVICE}/${SERVICE}_service /home/engineer/services/${SERVICE}/${SERVICE}_service
COPY --chown=engineer:engineer library/library /home/engineer/services/${SERVICE}/.venv/lib/python3.13/site-packages/library
WORKDIR /home/engineer/services/${SERVICE}

# final environment changes
ARG FEATURE_ENVIRONMENT=
ENV FEATURE_ENVIRONMENT=${FEATURE_ENVIRONMENT}

USER engineer
# so that there is something running when first deployed without a command provided
CMD ["python", "-m", "http.server", "8080"]
