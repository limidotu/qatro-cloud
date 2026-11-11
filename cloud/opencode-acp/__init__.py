"""OpenCode ACP provider profile.

Drives a local ``opencode acp`` subprocess over stdio. OpenCode supplies the
model and its own tool loop; Hermes keeps the conversation, Discord transport,
and approvals. Free OpenCode models are only reachable from inside OpenCode, so
the subprocess is the supported path.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from providers import register_provider
from providers.base import ProviderProfile

def _resolve_default_command() -> str:
    """Env override, then the Linux opencode launchers, then the Windows default."""
    env = os.environ.get("HERMES_OPENCODE_ACP_COMMAND", "").strip()
    if env:
        return env
    for candidate in (Path.home() / ".local" / "bin" / "opencode-nice",
                      Path.home() / ".local" / "bin" / "opencode"):
        if candidate.exists():
            return str(candidate)
    return str(Path.home() / "AppData" / "Roaming" / "npm" / "node_modules"
               / "@opencode" / "cli" / "bin" / "opencode.exe")


_DEFAULT_COMMAND = Path(_resolve_default_command())
_WORKDIR = os.environ.get("HERMES_OPENCODE_ACP_CWD", str(Path.home() / "workspace"))
_FREE_MODEL = "opencode/deepseek-v4.1-flash-free"
_GLM_MODEL = "opencode/glm-5.3-flash-free"
_FREE_MODELS = (_FREE_MODEL, _GLM_MODEL)

# Models the local `opencode acp` server currently advertises. The live ACP
# picker is authoritative; this list keeps the Hermes picker populated when
# the probe cannot run (for example, when OpenCode is not installed or is
# still starting).
_FALLBACK_MODEL_IDS = _FREE_MODELS


class OpenCodeACPProfile(ProviderProfile):
    """OpenCode's ACP server as an external-process provider."""

    def discover_models(self, **_: Any) -> list[dict[str, Any]] | None:
        """Return the live model list advertised by the local OpenCode ACP server."""
        client = None
        try:
            client = self.create_client()
            model_ids = client.list_models(timeout_seconds=20.0)
        except Exception:
            return None
        finally:
            if client is not None:
                client.close()
        rows: list[dict[str, Any]] = []
        for model_id in model_ids or ():
            model_id = str(model_id or "").strip()
            if not model_id:
                continue
            label = model_id.split("/", 1)[1] if "/" in model_id else model_id
            rows.append({"id": model_id, "label": label, "note": ""})
        return rows or None

    def create_client(self, **client_kwargs: Any) -> Any:
        from agent.copilot_acp_client import CopilotACPClient, _model_selection_request

        class _OpenCodeClient(CopilotACPClient):
            def _run_prompt(self, prompt_text: str, *, timeout_seconds: float,
                            model: str | None = None) -> tuple[str, str]:
                requested = str(model or _FREE_MODEL).strip()
                if requested and "/" not in requested:
                    requested = f"opencode/{requested}"
                if requested not in _FREE_MODELS:
                    raise ValueError("Only the configured free OpenCode models are allowed.")
                with self._session(timeout_seconds) as (session, request):
                    selection = _model_selection_request(session, requested)
                    if selection is None:
                        raise RuntimeError("The requested free model is unavailable.")
                    result = request(*selection)
                    options = result.get("configOptions", []) if isinstance(result, dict) else []
                    option = next((item for item in options if isinstance(item, dict)
                                   and "model" in (item.get("category"), item.get("id"))), None)
                    if not option or option.get("currentValue") != requested:
                        raise RuntimeError("OpenCode did not confirm the free model selection.")
                    text_parts: list[str] = []
                    reasoning_parts: list[str] = []
                    request("session/prompt", {"sessionId": session["sessionId"],
                            "prompt": [{"type": "text", "text": prompt_text}]},
                            text_parts=text_parts, reasoning_parts=reasoning_parts)
                    return "".join(text_parts), "".join(reasoning_parts)

        kwargs = dict(client_kwargs)
        kwargs["acp_command"] = kwargs.get("acp_command") or str(_DEFAULT_COMMAND)
        kwargs["acp_args"] = kwargs.get("acp_args") or ["acp"]
        kwargs["acp_cwd"] = kwargs.get("acp_cwd") or _WORKDIR
        return _OpenCodeClient(**kwargs)


opencode_acp = OpenCodeACPProfile(
    name="opencode-acp",
    aliases=("opencode-acp-agent",),
    display_name="OpenCode ACP",
    description="OpenCode agent over ACP (local subprocess)",
    api_mode="chat_completions",
    base_url="acp://opencode",
    auth_type="external_process",
    supports_health_check=False,
    supports_model_listing=False,
    process_command=str(_DEFAULT_COMMAND),
    process_args=("acp",),
    process_command_env_vars=("HERMES_OPENCODE_ACP_COMMAND", "OPENCODE_CLI_PATH"),
    process_args_env_var="HERMES_OPENCODE_ACP_ARGS",
    fallback_models=_FALLBACK_MODEL_IDS,
)

register_provider(opencode_acp)
