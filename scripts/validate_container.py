"""Exercise the production container contract with disposable resources only."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, NoReturn
from uuid import uuid4

EXPECTED_HEALTH = {
    "status": "ok",
    "service": "opsmind-api",
    "environment": "test",
}
EXPECTED_MEMORY_READY = {
    "status": "ready",
    "service": "opsmind-api",
    "environment": "test",
    "backend": "memory",
    "checks": {"persistence": "ready"},
}
EXPECTED_POSTGRESQL_READY = {
    "status": "ready",
    "service": "opsmind-api",
    "environment": "test",
    "backend": "postgresql",
    "checks": {"persistence": "ready"},
}
EXPECTED_POSTGRESQL_NOT_READY = {
    "status": "not_ready",
    "service": "opsmind-api",
    "environment": "test",
    "backend": "postgresql",
    "checks": {"persistence": "not_ready"},
}


@dataclass(frozen=True, slots=True)
class SyntheticCredentials:
    """One short-lived key and token pair generated inside the target image."""

    public_key: str
    token: str


class ContainerValidationError(RuntimeError):
    """Signal a bounded container-contract failure."""


def run(
    arguments: Sequence[str],
    *,
    check: bool = True,
    timeout: float = 180.0,
) -> subprocess.CompletedProcess[str]:
    """Run one explicit command without a shell."""
    return subprocess.run(
        arguments,
        check=check,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def docker(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run one Docker command."""
    return run(("docker", *arguments), check=check)


def fail(message: str) -> NoReturn:
    """Raise one consistent validation failure."""
    raise ContainerValidationError(message)


def image_inspect(image: str) -> dict[str, Any]:
    """Return the first Docker image-inspection record."""
    records = json.loads(docker("image", "inspect", image).stdout)
    if not isinstance(records, list) or len(records) != 1:
        fail("Docker returned an unexpected image inspection result")
    record = records[0]
    if not isinstance(record, dict):
        fail("Docker image inspection was not an object")
    return record


def assert_image_contract(image: str) -> None:
    """Verify architecture, metadata, runtime user, contents, and dependencies."""
    record = image_inspect(image)
    config = record.get("Config")
    if not isinstance(config, dict):
        fail("Image configuration is missing")
    if record.get("Architecture") != "amd64" or record.get("Os") != "linux":
        fail("Image must be linux/amd64")
    if config.get("User") != "10001:10001":
        fail("Image runtime user must be 10001:10001")
    if config.get("WorkingDir") != "/app":
        fail("Image working directory must be /app")
    labels = config.get("Labels")
    if not isinstance(labels, dict):
        fail("OCI labels are missing")
    revision = labels.get("org.opencontainers.image.revision")
    if not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        fail("OCI revision must be one full Git commit SHA")
    expected_labels = {
        "org.opencontainers.image.title": "OpsMind API",
        "org.opencontainers.image.source": "https://github.com/AnishPaudyal/opsmind",
        "org.opencontainers.image.version": "0.1.0",
    }
    if any(labels.get(key) != value for key, value in expected_labels.items()):
        fail("Required OCI identity labels are incorrect")
    healthcheck = config.get("Healthcheck")
    if not isinstance(healthcheck, dict) or "/health" not in str(healthcheck):
        fail("Docker health check must target /health")
    command = config.get("Cmd")
    if "uvicorn" not in str(command) or "--workers 1" not in str(command):
        fail("Image command must run one Uvicorn worker")
    configured_environment = config.get("Env")
    if not isinstance(configured_environment, list) or any(
        str(value).startswith(("OPSMIND_DATABASE_URL=", "OPSMIND_AUTH_PUBLIC_KEY="))
        for value in configured_environment
    ):
        fail("Image configuration contains a runtime secret setting")

    package_check = docker(
        "run",
        "--rm",
        image,
        "python",
        "-c",
        (
            "import importlib.util, opsmind; "
            "assert '/site-packages/opsmind' in str(opsmind.__file__); "
            "assert all(importlib.util.find_spec(name) is None "
            "for name in ('pip', 'pytest', 'ruff', 'mypy', 'pytest_cov')); "
            "print(opsmind.__file__)"
        ),
    )
    if "/site-packages/opsmind" not in package_check.stdout:
        fail("OpsMind is not installed as a production package")

    content_check = docker(
        "run",
        "--rm",
        image,
        "python",
        "-c",
        (
            "from pathlib import Path; "
            "assert Path('/app/alembic.ini').is_file(); "
            "assert Path('/app/migrations/env.py').is_file(); "
            "assert not any(Path('/app').joinpath(name).exists() "
            "for name in ('tests', 'src', '.git', '.env', 'docs'))"
        ),
    )
    if content_check.returncode != 0:
        fail("Image content boundary is incorrect")

    history = docker("history", "--no-trunc", image).stdout
    forbidden_history = (
        "BEGIN PRIVATE KEY",
        "OPSMIND_DATABASE_URL=",
        "OPSMIND_AUTH_PUBLIC_KEY=",
        "POSTGRES_PASSWORD=",
    )
    if any(marker in history for marker in forbidden_history):
        fail("Image history contains a forbidden secret/configuration marker")

    size_bytes = record.get("Size")
    if not isinstance(size_bytes, int):
        fail("Image size is unavailable")
    print(f"image_size_bytes={size_bytes}")
    print(f"image_size_mib={size_bytes / 1024 / 1024:.2f}")


def generate_credentials(image: str) -> SyntheticCredentials:
    """Generate a short-lived synthetic RS256 identity inside the image."""
    source = """
import json
from datetime import UTC, datetime, timedelta
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()
now = datetime.now(UTC)
token = jwt.encode(
    {
        "iss": "https://phase8a.invalid",
        "aud": "opsmind-api",
        "sub": "phase8a-container-smoke",
        "exp": now + timedelta(minutes=10),
        "nbf": now - timedelta(seconds=1),
        "permissions": ["business:read"],
    },
    private_key,
    algorithm="RS256",
)
print(json.dumps({"public_key": public_key, "token": token}))
"""
    result = docker("run", "--rm", image, "python", "-c", source)
    payload = json.loads(result.stdout)
    return SyntheticCredentials(
        public_key=str(payload["public_key"]),
        token=str(payload["token"]),
    )


def container_port(name: str, target_port: int) -> int:
    """Return the dynamically published loopback port for one API container."""
    output = docker("port", name, f"{target_port}/tcp").stdout.strip()
    try:
        return int(output.rsplit(":", maxsplit=1)[1])
    except (IndexError, ValueError):
        fail(f"Could not resolve the published port for {name}")


def request_json(
    port: int,
    path: str,
    *,
    token: str | None = None,
) -> tuple[int, Any]:
    """Perform one loopback request and return status plus JSON body."""
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def wait_for_health(name: str, port: int) -> None:
    """Wait until the API returns its exact process-liveness contract."""
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            status, payload = request_json(port, "/health")
            if status == 200 and payload == EXPECTED_HEALTH:
                return
        except (OSError, ValueError):
            pass
        time.sleep(0.5)
    log_result = docker("logs", "--tail", "50", name, check=False)
    logs = f"{log_result.stdout}{log_result.stderr}"
    fail(f"{name} did not become healthy; bounded logs:\n{logs}")


def application_arguments(
    name: str,
    network: str,
    image: str,
    credentials: SyntheticCredentials,
    *,
    database_url: str | None = None,
    port: int = 8000,
) -> list[str]:
    """Build hardened Docker arguments for one disposable API instance."""
    arguments = [
        "run",
        "--detach",
        "--name",
        name,
        "--network",
        network,
        "--publish",
        f"127.0.0.1::{port}",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=16777216",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--env",
        f"PORT={port}",
        "--env",
        "OPSMIND_ENVIRONMENT=test",
        "--env",
        "OPSMIND_AUTH_ISSUER=https://phase8a.invalid",
        "--env",
        "OPSMIND_AUTH_AUDIENCE=opsmind-api",
        "--env",
        f"OPSMIND_AUTH_PUBLIC_KEY={credentials.public_key}",
    ]
    if database_url is not None:
        arguments.extend(
            (
                "--env",
                "OPSMIND_PERSISTENCE_BACKEND=postgresql",
                "--env",
                f"OPSMIND_DATABASE_URL={database_url}",
            )
        )
    arguments.append(image)
    return arguments


def assert_runtime_process(name: str) -> None:
    """Verify the container and PID 1 both run as the bounded non-root user."""
    uid = docker("exec", name, "id", "-u").stdout.strip()
    pid_one = docker(
        "exec",
        name,
        "python",
        "-c",
        "print(open('/proc/1/cmdline', 'rb').read().replace(b'\\0', b' ').decode())",
    ).stdout
    if uid != "10001" or "uvicorn" not in pid_one:
        fail(f"{name} is not running Uvicorn as non-root PID 1")


def stop_gracefully(name: str) -> None:
    """Stop one API with SIGTERM and require a successful process exit."""
    docker("stop", "--time", "10", name)
    exit_code = docker(
        "inspect",
        "--format",
        "{{.State.ExitCode}}",
        name,
    ).stdout.strip()
    if exit_code != "0":
        fail(f"{name} did not stop cleanly; exit code {exit_code}")


def wait_for_docker_health(name: str) -> None:
    """Require Docker's configured liveness probe to report healthy."""
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        status = docker(
            "inspect",
            "--format",
            "{{.State.Health.Status}}",
            name,
        ).stdout.strip()
        if status == "healthy":
            return
        if status == "unhealthy":
            fail(f"Docker health check failed for {name}")
        time.sleep(0.5)
    fail(f"Docker health check did not complete for {name}")


def validate_memory(
    network: str,
    image: str,
    credentials: SyntheticCredentials,
    names: set[str],
    suffix: str,
) -> None:
    """Validate memory startup, health, readiness, auth, and shutdown."""
    name = f"opsmind-memory-{suffix}"
    target_port = 8765
    docker(
        *application_arguments(
            name,
            network,
            image,
            credentials,
            port=target_port,
        )
    )
    names.add(name)
    port = container_port(name, target_port)
    wait_for_health(name, port)
    wait_for_docker_health(name)
    assert_runtime_process(name)
    if request_json(port, "/health") != (200, EXPECTED_HEALTH):
        fail("Memory container liveness contract failed")
    if request_json(port, "/ready") != (200, EXPECTED_MEMORY_READY):
        fail("Memory container readiness contract failed")
    if request_json(port, "/api/v1/products")[0] != 401:
        fail("Unauthenticated protected request did not return 401")
    if request_json(
        port,
        "/api/v1/products",
        token=credentials.token,
    ) != (200, []):
        fail("Authenticated protected request did not succeed")
    stop_gracefully(name)


def wait_for_postgresql(name: str) -> None:
    """Wait for the disposable PostgreSQL 17 service."""
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        result = docker(
            "exec",
            name,
            "pg_isready",
            "-U",
            "opsmind",
            "-d",
            "opsmind_test",
            check=False,
        )
        if result.returncode == 0:
            return
        time.sleep(0.5)
    fail("Disposable PostgreSQL 17 did not become ready")


def validate_postgresql(
    network: str,
    image: str,
    credentials: SyntheticCredentials,
    names: set[str],
    suffix: str,
) -> None:
    """Validate unmigrated/migrated readiness and external migrations."""
    postgres_name = f"opsmind-postgresql-{suffix}"
    password = "opsmind-phase8a-synthetic-only"
    database_url = (
        f"postgresql+psycopg://opsmind:{password}@{postgres_name}:5432/opsmind_test"
    )
    docker(
        "run",
        "--detach",
        "--name",
        postgres_name,
        "--network",
        network,
        "--env",
        "POSTGRES_DB=opsmind_test",
        "--env",
        "POSTGRES_USER=opsmind",
        "--env",
        f"POSTGRES_PASSWORD={password}",
        "postgres:17-alpine",
    )
    names.add(postgres_name)
    wait_for_postgresql(postgres_name)

    unmigrated_name = f"opsmind-unmigrated-{suffix}"
    docker(
        *application_arguments(
            unmigrated_name,
            network,
            image,
            credentials,
            database_url=database_url,
        )
    )
    names.add(unmigrated_name)
    unmigrated_port = container_port(unmigrated_name, 8000)
    wait_for_health(unmigrated_name, unmigrated_port)
    if request_json(unmigrated_port, "/ready") != (
        503,
        EXPECTED_POSTGRESQL_NOT_READY,
    ):
        fail("Unmigrated PostgreSQL must report not ready")
    table_absent = docker(
        "exec",
        postgres_name,
        "psql",
        "-U",
        "opsmind",
        "-d",
        "opsmind_test",
        "-Atqc",
        "SELECT to_regclass('public.alembic_version') IS NULL",
    ).stdout.strip()
    if table_absent != "t":
        fail("Application startup changed the unmigrated database")
    stop_gracefully(unmigrated_name)

    docker(
        "run",
        "--rm",
        "--network",
        network,
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=16777216",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--env",
        f"OPSMIND_DATABASE_URL={database_url}",
        image,
        "alembic",
        "upgrade",
        "head",
    )
    revision = docker(
        "exec",
        postgres_name,
        "psql",
        "-U",
        "opsmind",
        "-d",
        "opsmind_test",
        "-Atqc",
        "SELECT version_num FROM alembic_version",
    ).stdout.strip()
    if revision != "0006_workflow_persistence":
        fail(f"Unexpected migrated revision: {revision}")

    migrated_name = f"opsmind-migrated-{suffix}"
    docker(
        *application_arguments(
            migrated_name,
            network,
            image,
            credentials,
            database_url=database_url,
        )
    )
    names.add(migrated_name)
    migrated_port = container_port(migrated_name, 8000)
    wait_for_health(migrated_name, migrated_port)
    if request_json(migrated_port, "/ready") != (
        200,
        EXPECTED_POSTGRESQL_READY,
    ):
        fail("Migrated PostgreSQL readiness contract failed")
    if request_json(migrated_port, "/api/v1/products")[0] != 401:
        fail("PostgreSQL-backed protected request did not return 401")
    if request_json(
        migrated_port,
        "/api/v1/products",
        token=credentials.token,
    ) != (200, []):
        fail("Authenticated PostgreSQL-backed request did not succeed")
    stop_gracefully(migrated_name)


def cleanup(network: str, names: set[str]) -> None:
    """Remove only resources created by this invocation."""
    for name in sorted(names, reverse=True):
        docker("rm", "--force", name, check=False)
    docker("network", "rm", network, check=False)


def parse_arguments() -> argparse.Namespace:
    """Parse the bounded local/CI validation interface."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument(
        "--mode",
        choices=("full", "memory"),
        default="full",
        help="Use memory for a repeat-build equivalence check; full also tests PostgreSQL.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the complete disposable validation and report concise evidence."""
    arguments = parse_arguments()
    image = str(arguments.image)
    mode = str(arguments.mode)
    suffix = uuid4().hex[:10]
    network = f"opsmind-phase8a-{suffix}"
    names: set[str] = set()
    docker("network", "create", network)
    try:
        assert_image_contract(image)
        credentials = generate_credentials(image)
        validate_memory(network, image, credentials, names, suffix)
        if mode == "full":
            validate_postgresql(network, image, credentials, names, suffix)
    finally:
        cleanup(network, names)
    print(f"container_validation=passed mode={mode} image={image}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
