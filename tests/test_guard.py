"""The Bash guard blocks dangerous commands, but not text that merely mentions them."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "guard_bash.py"


def run(cmd: str, cwd: Path) -> int:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": str(cwd)})
    return subprocess.run(
        [sys.executable, str(GUARD)], input=payload, text=True, capture_output=True
    ).returncode


BLOCKED = [
    "git push --force origin main",
    'git push "--force" origin main',
    "git push -f",
    "git reset --hard HEAD~3",
    "aws s3 rm s3://bucket --recursive",
    "aws lambda delete-function --function-name x",
    "gcloud run services delete app",
    "rm -rf /",
    'rm -rf "/"',
    "rm -rf ~",
    "make teardown-aws",
    'bash -c "git push --force"',
    "eval 'git reset --hard'",
    'echo "$(git push --force)"',
    "bash <<'EOF'\ngit push --force\nEOF",
    "cat <<EOF | sh\ngit reset --hard\nEOF",
    "cat > a.md <<'EOF'\nhello\nEOF\ngit push --force",  # command after the heredoc
    "git add .env",
    # reading secrets into the conversation
    "cat .env",
    "cat ./.env.local",
    "head -5 .env",
    "grep KEY .env",
    "less ~/.aws/credentials",
    "source .env",
    ". ./.env",
    "base64 key.pem",
    "cp .env /tmp/x",
    "sort < .env",
    "printenv",
    "env",
    "env | grep AWS",
    "python3 -c \"print(open('.env').read())\"",
    "python3 - <<'EOF'\nprint(open('.env').read())\nEOF",
    "python3 -c \"from pathlib import Path; print(Path('./.env.local').read_text())\"",
    "node -e \"console.log(require('fs').readFileSync('.env','utf8'))\"",
    "python3 -c \"print(open('/home/me/.aws/credentials').read())\"",
]

ALLOWED = [
    "git push origin main",
    "git push --force-with-lease",
    "cat > README.md <<'EOF'\nNever run git push --force or rm -rf / here.\nEOF",
    "cat > notes.md <<-EOF\n\taws s3 rm is blocked for agents\n\tEOF",
    'git commit -m "docs: explain why agents never git push --force"',
    "echo 'make teardown-aws is human-only'",
    "rm -rf /tmp/build",
    "rm -rf node_modules",
    "ls -la",
    # secrets-adjacent but fine
    "cat .env.example",
    "cp .env.example .env",
    "grep -n .env Makefile",  # .env is the pattern, not the file
    "ls -la .env",
    "env LLM_PROVIDER=mock pytest",
    "make deploy-aws",
    "python3 -c 'print(1)'",
    "python3 - <<'EOF'\nprint('docs: never cat .env, use make')\nEOF",  # mentions, doesn't open
    "python3 -c \"open('.env.example').read()\"",
]


@pytest.mark.parametrize("cmd", BLOCKED)
def test_blocks(cmd, tmp_path):
    assert run(cmd, tmp_path) == 2, cmd


@pytest.mark.parametrize("cmd", ALLOWED)
def test_allows(cmd, tmp_path):
    assert run(cmd, tmp_path) == 0, cmd
