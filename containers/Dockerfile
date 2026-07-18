# uavsim — single-image study runner (Phase 4 systems demo)
# Build from repo root:
#   docker build -t uavsim:local -f containers/Dockerfile .
#
# Run a documented smoke study (mount host repo for configs + runs):
#   docker run --rm -v "$PWD":/work -w /work uavsim:local \
#     study configs/studies/hover_mc_smoke.yaml --output runs
#
# Note: package lives under /opt/uavsim so a host bind-mount on /work
# does not hide the image virtualenv.

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH="/opt/uavsim/.venv/bin:$PATH"

WORKDIR /opt/uavsim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.7.12 /uv /usr/local/bin/uv

# Dependency + package install (lockfile-reproducible)
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

# Bake configs for offline demos (host /work mount still preferred for authoring)
COPY configs ./configs

WORKDIR /work
ENTRYPOINT ["uavsim"]
CMD ["--help"]
