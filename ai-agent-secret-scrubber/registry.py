"""Secret registry: collects key-value pairs from .env and credentials files."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path


# Patterns that look like secret keys in .env files
SECRET_KEY_PATTERNS = [
    re.compile(r"(key|secret|token|password|passwd|pwd|api_key|apikey|auth)", re.IGNORECASE),
]

# Minimum value length to consider as a potential secret
MIN_SECRET_LENGTH = 8


class SecretRegistry:
    """Stores known secrets collected from config files."""

    def __init__(self) -> None:
        self._secrets: dict[str, str] = {}  # key -> value
        self._loaded_files: set[str] = set()

    @property
    def secrets(self) -> dict[str, str]:
        return dict(self._secrets)

    @property
    def values(self) -> list[str]:
        return list(self._secrets.values())

    def add(self, key: str, value: str) -> None:
        if value and len(value) >= MIN_SECRET_LENGTH:
            self._secrets[key] = value

    def load_env_file(self, path: str | Path) -> int:
        """Parse a .env file and collect secret-like key-value pairs.

        .env files are inherently sensitive — collect all values above
        minimum length since they typically contain configuration secrets.

        Returns the number of secrets collected.
        """
        path = Path(path).resolve()
        if not path.is_file():
            return 0

        # Prevent double-loading the same file
        path_str = str(path)
        if path_str in self._loaded_files:
            return 0
        self._loaded_files.add(path_str)

        count = 0
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.+)$', line)
            if not match:
                continue

            key, value = match.group(1), match.group(2)
            # Strip surrounding quotes
            value = value.strip().strip("'\"")

            if not value or len(value) < MIN_SECRET_LENGTH:
                continue

            # .env files are sensitive by nature — collect all sufficiently long values
            self._secrets[key] = value
            count += 1

        return count

    def load_credentials_json(self, path: str | Path) -> int:
        """Parse a credentials.json file and collect secret values.

        Returns the number of secrets collected.
        """
        path = Path(path)
        if not path.is_file():
            return 0

        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return 0

        count = 0
        count += self._extract_from_dict(data)
        return count

    def _extract_from_dict(self, data: dict | list, prefix: str = "") -> int:
        count = 0
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, str) and len(value) >= MIN_SECRET_LENGTH:
                    is_secret_key = any(p.search(key) for p in SECRET_KEY_PATTERNS)
                    if is_secret_key or self._looks_like_secret_value(value):
                        self._secrets[full_key] = value
                        count += 1
                elif isinstance(value, (dict, list)):
                    count += self._extract_from_dict(value, full_key)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    count += self._extract_from_dict(item, f"{prefix}[{i}]")
        return count

    def auto_discover(self, directory: str | Path = ".") -> int:
        """Scan a directory for .env and credentials files."""
        directory = Path(directory)
        count = 0

        # .env files
        for env_file in directory.glob("*.env"):
            count += self.load_env_file(env_file)
        env_default = directory / ".env"
        if env_default.is_file():
            count += self.load_env_file(env_default)

        # credentials.json
        for cred_file in directory.glob("*credentials*.json"):
            count += self.load_credentials_json(cred_file)

        return count

    @staticmethod
    def _looks_like_secret_value(value: str) -> bool:
        """Heuristic: does this value look like a secret?"""
        # Contains mix of upper, lower, digits — typical of API keys
        has_upper = any(c.isupper() for c in value)
        has_lower = any(c.islower() for c in value)
        has_digit = any(c.isdigit() for c in value)
        if has_upper and has_lower and has_digit and len(value) >= 16:
            return True
        # Starts with common prefixes
        if value.startswith(("sk-", "pk-", "ghp_", "gho_", "xoxb-", "xoxp-", "AKIA")):
            return True
        return False

    def summary(self) -> str:
        lines = [f"Secret Registry: {len(self._secrets)} secrets loaded"]
        for key in self._secrets:
            lines.append(f"  - {key}: {'*' * 8}")
        return "\n".join(lines)
