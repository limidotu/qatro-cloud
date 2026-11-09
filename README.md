# Quatro cloud

Deploy Quatro on an Oracle Always Free ARM server. Use the GitHub Pages control
page to open authenticated actions for Start, Stop, and Status.

The preferred target is 2 A1 cores, 12 GB RAM, and a 50 GB boot disk. Montreal
rejected both 2-core and 1-core A1 requests because of host capacity on November
8, 2026. The active deployment uses the fixed Always Free AMD micro shape with
1 GB RAM and a 50 GB disk. Runtime checks must pass before the final migration.
The controller accepts either approved shape. The provisioning tool still
targets A1 for a future migration. Free availability
depends on Oracle capacity and reclamation rules. Model availability depends on
OpenCode's free offers. This project does not guarantee a zero bill or uptime.

The live Windows setup is separate. This repository contains no personal memory,
conversation history, Discord credentials, or cloud keys.

## State

- The control page and workflows are implemented.
- Oracle provisioning and Linux migration tools are implemented.
- Live deployment needs Oracle account access and GitHub authentication.
- The page keeps its controls inactive until `QATRO_CLOUD_READY` is `true`.
- The default configuration includes only OpenCode free model IDs.

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

Make sure the custom provider imports, OpenCode advertises the chosen model,
and a local ACP exchange works. Then create the `.qatro-ready` marker in the
cloud Hermes home. Enable and start `qatro.service`. Test a Discord reply and
reboot recovery before disabling the Windows startup entry. Keep only one
gateway connected during the final switch.

Some imported skills depend on Windows software or desktop access. Their files
can migrate, but those capabilities need separate Linux replacements.

## Connect the GitHub controls

Use a dedicated Oracle identity for control. Limit it to reading and changing
the power state of this one instance. The following policy is a template:

```text
Allow group QuatroControl to manage instances in compartment id YOUR_COMPARTMENT_OCID where all {target.instance.id = 'YOUR_INSTANCE_OCID', any {request.permission = 'INSTANCE_READ', request.permission = 'INSTANCE_POWER_ACTIONS'}}
```

Use the identity-domain form of the group name where the account requires it.
The controller checks the instance's `qatro-managed=true` tag and approved free
shape before any operation. Its credential cannot create or delete resources
when the policy restricts it as shown.

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
After the live checks pass, set `QATRO_CLOUD_READY=true` and run **Publish Quatro
controls**. The build writes the repository name into the page configuration.
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
- [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)
