# OpenCode provider

This prepared provider runs OpenCode through its Agent Client Protocol (ACP)
process. It accepts the free OpenCode models `opencode/deepseek-v4.1-flash-free`
and `opencode/glm-5.3-flash-free`. It confirms the model selection before it
sends a prompt. If OpenCode does not confirm the selection, the provider stops
instead of using another model.

The cloud server has OpenCode 2.2.5 at
`/home/qatro/.local/bin/opencode-2.2.5`. The gateway starts it through
`opencode-nice` at a lower CPU priority. Automatic chat titles do not make a
second model request. A copy of the
earlier provider remains next to the installed provider as
`__init__.py.quatro-original`. The model settings before the switch are in
`~/.hermes/quatro-model-before.yaml` on the server.

OpenCode free models have usage limits and availability can change. DeepSeek
is the configured default. The server's OpenCode Console login is connected
(`opencode auth list`), which restored the free quota after the anonymous
limit was reached. Both models were verified live through the provider:
DeepSeek and GLM each returned a reply. The 1 GB server remains slow, and
session creation occasionally fails with a transient
`Internal service failure` while OpenCode's location plugins are still
activating; retrying the request succeeds.
The user's Windows-only `pc` MCP server is disabled on Linux.

Run `python cloud/opencode-acp/test_safe_acp.py` to test the model guard.
