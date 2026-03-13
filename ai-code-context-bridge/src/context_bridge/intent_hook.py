"""Git hook for recording change intent metadata.

Generates a prepare-commit-msg hook that prompts for change intent
and stores it as JSON in .intent/ directory.
"""

import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path


HOOK_SCRIPT = textwrap.dedent("""\
    #!/bin/sh
    # ai-code-context-bridge: change intent recorder
    # Installed as .git/hooks/prepare-commit-msg

    COMMIT_MSG_FILE=$1
    INTENT_DIR=".intent"

    mkdir -p "$INTENT_DIR"

    # Get changed files
    CHANGED_FILES=$(git diff --cached --name-only)
    if [ -z "$CHANGED_FILES" ]; then
        exit 0
    fi

    # Generate intent metadata
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    HASH=$(date +%s%N | sha256sum | head -c 8)
    INTENT_FILE="$INTENT_DIR/${HASH}.json"

    # Build JSON (portable, no jq dependency)
    python3 -c "
import json, sys
files = '''$CHANGED_FILES'''.strip().split('\\n')
data = {
    'timestamp': '$TIMESTAMP',
    'branch': '$BRANCH',
    'files': files,
    'commit_msg_file': '$COMMIT_MSG_FILE',
}
with open('$INTENT_FILE', 'w') as f:
    json.dump(data, f, indent=2)
print(f'[context-bridge] Intent recorded: $INTENT_FILE', file=sys.stderr)
"
""")


def install_hook(repo_path: str | Path) -> str:
    """Install the prepare-commit-msg hook in a git repository."""
    repo = Path(repo_path)
    hooks_dir = repo / ".git" / "hooks"

    if not hooks_dir.exists():
        return f"Error: {hooks_dir} does not exist. Is this a git repository?"

    hook_path = hooks_dir / "prepare-commit-msg"
    hook_path.write_text(HOOK_SCRIPT)
    hook_path.chmod(0o755)

    # Create .intent directory
    intent_dir = repo / ".intent"
    intent_dir.mkdir(exist_ok=True)

    return f"Hook installed: {hook_path}\nIntent directory: {intent_dir}"


def record_intent(
    repo_path: str | Path,
    files: list[str],
    message: str = "",
    branch: str = "unknown",
) -> Path:
    """Manually record a change intent (for testing without git hook)."""
    repo = Path(repo_path)
    intent_dir = repo / ".intent"
    intent_dir.mkdir(exist_ok=True)

    now = datetime.now(timezone.utc)
    filename = now.strftime("%Y%m%d_%H%M%S") + ".json"
    intent_file = intent_dir / filename

    data = {
        "timestamp": now.isoformat(),
        "branch": branch,
        "files": files,
        "message": message,
    }

    intent_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return intent_file
