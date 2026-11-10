# OpenCode provider

This prepared provider runs OpenCode through its Agent Client Protocol (ACP)
process. It accepts only `opencode/deepseek-v4.1-flash-free`. It confirms the
model selection before it sends a prompt. If OpenCode does not confirm the
selection, the provider stops instead of using another model.

The cloud server has OpenCode 2.2.5 at
`/home/qatro/.local/bin/opencode-2.2.5`. The gateway starts it through
`opencode-nice` at a lower CPU priority. Automatic chat titles do not make a
second model request. A copy of the
earlier provider remains next to the installed provider as
`__init__.py.quatro-original`. The model settings before the switch are in
`~/.hermes/quatro-model-before.yaml` on the server.

OpenCode free models have usage limits and availability can change. DeepSeek
is the configured default because Cloudflare reached its daily free limit. A
full Hermes test returned a DeepSeek reply with the dashboard running after
the CPU priority change. The 1 GB server remains slow, and the automatic
Cloudflare fallback has not been tested end to end.
The user's Windows-only `pc` MCP server is disabled on Linux.

Run `python cloud/opencode-acp/test_safe_acp.py` to test the model guard.
