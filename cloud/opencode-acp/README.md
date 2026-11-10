# OpenCode provider

Quatro uses OpenCode through its Agent Client Protocol (ACP) process. The
provider accepts only `opencode/deepseek-v4.1-flash-free`. It confirms the
model selection before it sends a prompt. If OpenCode does not confirm the
selection, the provider stops instead of using another model.

The cloud server runs OpenCode 2.2.5 at
`/home/qatro/.local/bin/opencode-2.2.5`. The `qatro.service` override sets
`HERMES_OPENCODE_ACP_COMMAND` and `HERMES_OPENCODE_ACP_CWD`. A copy of the
earlier provider remains next to the installed provider as
`__init__.py.quatro-original`. The model settings before the switch are in
`~/.hermes/quatro-model-before.yaml` on the server.

OpenCode free models have usage limits and availability can change. Hermes
has a Cloudflare free-model fallback configured, but the automatic fallback
has not been tested end to end. The 1 GB server can take time to start an ACP
session. The user's Windows-only `pc` MCP server is disabled on Linux.

Run `python cloud/opencode-acp/test_safe_acp.py` to test the model guard.
