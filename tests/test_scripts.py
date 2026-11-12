"""Kickoff scripts: use_cloud.py (keep one cloud) and pin_mcp.py (pin MCP versions)."""

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def repo(tmp_path):
    dst = tmp_path / "repo"
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", ".venv", "node_modules"))
    return dst


def use(repo, cloud):
    return subprocess.run(
        [sys.executable, str(repo / "scripts" / "use_cloud.py"), cloud, "--root", str(repo)],
        capture_output=True,
        text=True,
    )


def test_use_aws_removes_gcp(repo):
    assert use(repo, "aws").returncode == 0
    assert not (repo / "deploy" / "gcp-cloudrun.sh").exists()
    assert (repo / "deploy" / "aws-lambda.sh").exists()
    assert set(json.loads((repo / ".mcp.json").read_text())["mcpServers"]) == {
        "aws",
        "aws-knowledge",
    }
    assert "google-genai" not in (repo / "requirements.txt").read_text()
    mk = (repo / "Makefile").read_text()
    assert "deploy-gcp" not in mk and "logs-gcp" not in mk and "deploy-aws:" in mk
    env = (repo / ".env.example").read_text()
    assert env.startswith("CLOUD=aws") and "GCP_PROJECT" not in env and "AWS_REGION" in env
    assert "LLM_PROVIDER=bedrock" in env
    # a second run refuses instead of deleting the other cloud too
    assert use(repo, "gcp").returncode != 0
    assert (repo / "deploy" / "aws-lambda.sh").exists()


def test_use_gcp_removes_aws(repo):
    assert use(repo, "gcp").returncode == 0
    assert not (repo / "deploy" / "iam").exists()
    assert set(json.loads((repo / ".mcp.json").read_text())["mcpServers"]) == {
        "cloud-run",
        "gcloud",
    }
    mk = (repo / "Makefile").read_text()
    assert "aws-bootstrap" not in mk and "teardown-aws" not in mk and "deploy-gcp:" in mk
    assert "boto3" not in (repo / "requirements.txt").read_text()
    env = (repo / ".env.example").read_text()
    assert "BEDROCK_MODEL_ID" not in env and "GCP_PROJECT" in env


def test_makefile_still_parses_after_pruning(repo):
    if not shutil.which("make"):
        pytest.skip("make not installed")
    use(repo, "aws")
    out = subprocess.run(["make", "-n", "help"], cwd=repo, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr


def test_pin_mcp_pins_unversioned_and_latest():
    pin = load("pin_mcp")
    cfg = json.loads((ROOT / ".mcp.json").read_text())
    changes = pin.pin(cfg, resolver=lambda cmd, pkg: "9.9.9")
    assert changes and not pin.unpinned(cfg)
    args = {n: s.get("args", []) for n, s in cfg["mcpServers"].items()}
    assert "mcp-proxy-for-aws@9.9.9" in args["aws"]
    assert "@google-cloud/cloud-run-mcp@9.9.9" in args["cloud-run"]
    assert pin.pin(cfg, resolver=lambda *_: "0.0.0") == []  # already pinned: untouched


def test_split_spec_handles_scopes():
    pin = load("pin_mcp")
    assert pin.split_spec("@google-cloud/gcloud-mcp") == ("@google-cloud/gcloud-mcp", "")
    assert pin.split_spec("@google-cloud/gcloud-mcp@1.2.0") == ("@google-cloud/gcloud-mcp", "1.2.0")
    assert pin.split_spec("mcp-proxy-for-aws@latest") == ("mcp-proxy-for-aws", "latest")
