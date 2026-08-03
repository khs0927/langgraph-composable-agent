"""
hermes.py — Adapter for subprocess calls to the hermes-ai CLI from inside LangGraph.

Ensures secrets (NVIDIA_API_KEY etc.) are never exposed in stderr replies.
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Optional


class HermesAdapter:
    """Wraps `minis-model-use` and `hermes-ai` shell tools."""

    def __init__(self, default_role: str = "fast"):
        self.default_role = default_role

    def run_model(self, payload: dict, timeout: int = 60) -> str:
        """Call `minis-model-use` via subprocess, returning output_text."""

        proc = subprocess.run(
            ["minis-model-use", "run", "--stdin"],
            input=json.dumps(payload),
            capture_output=True, text=True, timeout=timeout,
        )
        if proc.returncode != 0:
            cleaned = self._redact(proc.stderr)
            raise RuntimeError(f"Model failed: {cleaned}")

        try:
            data = json.loads(proc.stdout)
            if not data.get("ok"):
                err = data.get("error", {}).get("message", "error")
                raise RuntimeError(self._redact(str(err)))
            return data.get("data", {}).get("output_text", "")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Model output not valid JSON: {e}")

    def run_role(self, prompt: str, role: Optional[str] = None, timeout: int = 90) -> str:
        """Call `hermes-ai` with a specific role."""
        role_flag = role or self.default_role
        proc = subprocess.run(
            ["hermes-ai", prompt, "--role", role_flag],
            capture_output=True, text=True, timeout=timeout,
        )
        if proc.returncode != 0:
            raise RuntimeError(self._redact(proc.stderr))
        return proc.stdout.strip()

    def _redact(self, text: str) -> str:
        """Remove known API key values from string."""
        if not text:
            return ""
        for env_key in ("NVIDIA_API_KEY", "AEROLINK_API_KEY", "SMITHERY_API_KEY"):
            val = os.environ.get(env_key)
            if val and len(val) > 4:
                text = text.replace(val, f"$$REDACTED_{env_key}")
        return text