"""Docker-backed study / shard execution (host orchestrates containers)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        r = subprocess.run(
            ["docker", "info"],
            check=False,
            capture_output=True,
            timeout=15,
        )
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def default_image_name() -> str:
    return os.environ.get("UAVSIM_DOCKER_IMAGE", "uavsim:local")


def run_in_docker(
    *,
    image: str,
    workdir: Path,
    args: list[str],
    volumes: list[tuple[Path, str]] | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """
    Run ``docker run --rm`` with repo workdir mounted and CLI args.

    ``args`` is the argv after the image name (e.g. ``["study", "configs/...", ...]``).
    """
    workdir = workdir.resolve()
    cmd: list[str] = [
        "docker",
        "run",
        "--rm",
        "-w",
        "/work",
        "-v",
        f"{workdir}:/work",
    ]
    if volumes:
        for host, container in volumes:
            cmd.extend(["-v", f"{host.resolve()}:{container}"])
    if env:
        for k, v in env.items():
            cmd.extend(["-e", f"{k}={v}"])
    cmd.append(image)
    cmd.extend(args)
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def ensure_image(image: str, *, repo_root: Path, build: bool = True) -> None:
    """Build image from repo Dockerfile if missing and ``build`` is True."""
    inspect = subprocess.run(
        ["docker", "image", "inspect", image],
        check=False,
        capture_output=True,
    )
    if inspect.returncode == 0:
        return
    if not build:
        msg = f"Docker image not found: {image}"
        raise RuntimeError(msg)
    dockerfile = repo_root / "containers" / "Dockerfile"
    if not dockerfile.is_file():
        msg = f"Dockerfile not found: {dockerfile}"
        raise FileNotFoundError(msg)
    build_cmd = [
        "docker",
        "build",
        "-t",
        image,
        "-f",
        str(dockerfile),
        str(repo_root),
    ]
    result = subprocess.run(build_cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        msg = f"docker build failed:\n{result.stderr or result.stdout}"
        raise RuntimeError(msg)


def docker_study(
    study_path: Path,
    *,
    repo_root: Path,
    output_root: Path,
    image: str | None = None,
    n_trials: int | None = None,
    force_mc: bool | None = None,
    shards: int = 1,
    extra_args: list[str] | None = None,
) -> dict[str, Any]:
    """
    Run a full study inside one container (local shards if shards>1 inside).

    Mounts repo as /work so configs are shared with the host. Output under the
    repo is written relative to /work; output outside the repo is bind-mounted
    at /out.
    """
    image = image or default_image_name()
    ensure_image(image, repo_root=repo_root)
    study_path = study_path.resolve()
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    study_arg = _path_in_container(study_path, repo_root, work_mount="/work")
    out_arg, extra_vols = _output_mount(output_root, repo_root)

    args = [
        "study",
        study_arg,
        "--output",
        out_arg,
        "--backend",
        "local",
        "--shards",
        str(shards),
    ]
    if n_trials is not None:
        args.extend(["--n-trials", str(n_trials)])
    if force_mc is True:
        args.append("--mc")
    elif force_mc is False:
        args.append("--no-mc")
    if extra_args:
        args.extend(extra_args)
    proc = run_in_docker(
        image=image,
        workdir=repo_root,
        args=args,
        volumes=extra_vols or None,
    )
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "image": image,
        "args": args,
    }


def _path_in_container(path: Path, repo_root: Path, *, work_mount: str) -> str:
    path = path.resolve()
    root = repo_root.resolve()
    try:
        rel = path.relative_to(root)
    except ValueError as exc:
        msg = f"Study path must be under repo root for docker mounts: {path} not in {root}"
        raise ValueError(msg) from exc
    return f"{work_mount}/{rel.as_posix()}"


def _output_mount(
    output_root: Path, repo_root: Path
) -> tuple[str, list[tuple[Path, str]]]:
    """Return (container output path, extra volume mounts)."""
    root = repo_root.resolve()
    try:
        rel = output_root.resolve().relative_to(root)
        return f"/work/{rel.as_posix()}", []
    except ValueError:
        return "/out", [(output_root.resolve(), "/out")]
