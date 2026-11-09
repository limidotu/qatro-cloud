# Quatro cloud

Deploy Quatro on an Oracle Always Free ARM server. Use the GitHub Pages control
page to open authenticated actions for Start, Stop, and Status.

The preferred target is 2 A1 cores, 12 GB RAM, and a 50 GB boot disk. Montreal
rejected both 2-core and 1-core A1 requests because of host capacity on November
8, 2026. The active deployment uses the fixed Always Free AMD micro shape with
1 GB RAM and a 50 GB disk. Runtime checks must pass before the final migration.
The controller accepts either approved shape. The provisioning tool still
targets A1 for a future migration. Free availability
depends on Oracle capacity and reclamation rules. Model availability depends on the selected provider's free offers. This project does not guarantee a zero bill or uptime.

The live Windows setup is separate. This repository contains no personal memory,
conversation history, Discord credentials, or cloud keys.

## State

- The control page and workflows are implemented.
- The Always Free server and dedicated control identity are provisioned.
- The cloud gateway connects to Discord. A real Discord reply remains to be checked.
- The PC gateway and its two restart tasks are disabled during the cloud switch.
- The active cloud configuration uses Cloudflare Workers AI on its free plan.
  Requests stop when its daily free allowance is exhausted.
- The page can enable server controls after power tests pass. A running server does not mean the cloud bot is active.
- The initial configuration includes only OpenCode free model IDs. The current
  server uses a separately configured Cloudflare free model.

## Account setup

Use an existing Oracle account if one exists. Oracle allows one free account per
person. Keep the tenancy on the free plan. Complete identity and card checks on
Oracle's site. Do not send passwords, card numbers, or keys through chat.

Use a public GitHub repository for free Pages hosting. Upload only this project.
Do not upload the Windows Hermes home or private migration archives.

## Provision the server

Install `requirements-control.txt` in a separate Python environment. Configure
the official OCI SDK outside this repository. Use the account's home region.

First run a read-only plan:

```text
python scripts/provision.py --compartment YOUR_COMPARTMENT_OCID
```

The plan checks existing A1 allocations and disk volumes across accessible
compartments. It refuses a different region, an existing A1 allocation, or a
new disk that would exceed 200 GB. Account permissions must allow this inventory.
The check does not replace Oracle's billing and quota controls. Other projects
can consume allowances after the check.

To create the server:

```text
python scripts/provision.py --compartment YOUR_COMPARTMENT_OCID --apply --ssh-public-key PATH_TO_PUBLIC_KEY --admin-cidr YOUR_IPV4/32
```

The tool creates a dedicated network and opens SSH only to the specified
administrator address. Discord needs no inbound web port. The tool never creates
a paid fallback. Resource IDs remain in ignored `.private/oci-state.json`.
If provisioning fails, inspect that file and Oracle before retrying.

The server installs the same public Hermes commit as the inspected Windows
source, plus OpenCode 2.2.5. It does not start the Discord gateway.

## Migrate private state

Stop the Windows gateway during the final migration. Keep the local data as a
rollback copy. Run the exporter on Windows with a destination outside this
repository:

```text
python scripts/export_state.py --home PATH_TO_ACTIVE_HERMES_HOME --destination PATH_TO_PRIVATE_ARCHIVE.tar.gz
```

The exporter copies memory, personality, sessions, skills, selected databases,
and the custom OpenCode provider. SQLite backups include committed data in the
write-ahead log. The exporter excludes `.env`, authentication files, key files,
and process locks. Treat the archive as private even though it excludes known
credential files. Conversations can contain private information.

Send the archive over authenticated SSH. Extract `home/` into the cloud Hermes
home with ownership `qatro:qatro`. Copy this repository to the cloud server.
Keep private state outside the repository.

As the `qatro` user, run:

```text
python3 PATH_TO_PROJECT/scripts/prepare_home.py
```

This writes a new Linux configuration and an OpenCode MCP configuration. The
existing Hermes configuration receives a backup. The tool refuses Windows and
an active cloud ready marker. File tools use the cloud workspace. Shell commands
run as the service user and are not a security sandbox.

Place the required Discord credentials in the cloud Hermes `.env` through a
private channel. Preserve the Discord user allowlist and channel behavior.
Do not transfer unrelated provider credentials. Put `cloud/CLOUD.md` in the
workspace so the agent knows that historical PC paths are unavailable.

Choose and test a free inference provider before enabling the gateway. The
initial OpenCode free models returned a usage-limit error from this server.
The current cloud setup uses Cloudflare Workers AI with a limited token stored
only on the server. It uses `@cf/openai/gpt-oss-120b` and a 128,000-token
context setting. A direct model and tool-call check, plus a Hermes prompt,
passed. Cloudflare receives the prompts and relevant conversation context.
Its free allowance is limited and model availability can change.

Make sure the selected model responds through Hermes. Then create the `.qatro-ready` marker in the
cloud Hermes home. Enable and start `qatro.service`. Test a Discord reply and
reboot recovery before disabling the Windows startup entry. Keep only one
gateway connected during the final switch.

Some imported skills depend on Windows software or desktop access. Their files
can migrate, but those capabilities need separate Linux replacements.

## Connect the GitHub controls

Use a dedicated Oracle identity for control. Oracle's core-service policy
reference does not document an instance-ID condition for Compute power actions.
Do not use an unverified instance-ID condition to claim access is limited to one
server. The Quatro compartment limits the account to instances inside that compartment.
Do not add other instances to it without reviewing the policy. Oracle's power permission
also allows actions such as restart and forced shutdown. The control page offers
only Start, Stop, and Status. Do not enable it until the policy scope and live
checks are confirmed.

Set these GitHub Actions secrets:

- `OCI_TENANCY_OCID`
- `OCI_USER_OCID`
- `OCI_FINGERPRINT`
- `OCI_PRIVATE_KEY`

Set these repository variables:

- `OCI_REGION`
- `OCI_INSTANCE_OCID`
- `QATRO_CLOUD_READY`: keep `false` until live checks pass

Enable GitHub Pages with GitHub Actions as its source. Run **Check Quatro status**.
After server power checks pass, set `QATRO_CLOUD_READY=true` and run **Publish Quatro
controls**. Keep the page notice accurate until the Discord migration passes. The build writes the repository name into the page configuration.
No credentials enter the Pages artifact.

Start and Stop share a concurrency group. Stop requests a graceful cloud
shutdown. Start and Stop wait up to 15 minutes for the requested state.
Status only reads state. A running server is not proof of bot health.

## Checks

```text
python -B -m unittest discover -s tests -v
node --test tests/site.test.js
bash -n cloud/bootstrap.sh
```

## Sources

- [Oracle free allowances](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- [Oracle access permissions](https://docs.oracle.com/en-us/iaas/Content/Identity/Reference/corepolicyreference.htm)
- [Hermes platform support](https://hermes-agent.nousresearch.com/docs/getting-started/platform-support)
- [OpenCode models and free offers](https://opencode.ai/docs/console/models/)
- [Cloudflare Workers AI free allowance](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)

## Switch Discord chats

Quatro has four Discord slash commands. Type `/` in the conversation and choose
Quatro's command from Discord's picker.

1. Use `/new` to start a fresh chat.
2. Use `/title name` to name the current chat.
3. Use `/sessions` or `/resume` to see named chats.
4. Use `/resume name` or `/resume number` to switch back to one.

Each chat keeps its own conversation history. Quatro's shared memory and
personality still apply. Starting a chat does not delete older conversations.
Very large imported chats can exceed the cloud model's context limit.

The cloud setup registers only these four commands with
`scripts/register_chat_commands.py --apply`. It does not overwrite existing
commands. The bot token is passed privately in the environment. The gateway's
Discord command synchronization stays off so it does not replace other commands.
