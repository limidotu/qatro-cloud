"""Start, stop, or inspect one tagged Oracle A1 server. Never create resources."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

SHAPE = "VM.Standard.A1.Flex"
TAG = "qatro-managed"


def validate_instance(instance):
    if (instance.freeform_tags or {}).get(TAG) != "true":
        raise ValueError("The configured instance does not have Qatro's management tag.")
    shape = instance.shape_config
    if instance.shape != SHAPE or shape is None:
        raise ValueError("The instance is not an Oracle A1 server.")
    if not (0 < shape.ocpus <= 2 and 0 < shape.memory_in_gbs <= 12):
        raise ValueError("The instance exceeds this project's free-size limits.")


def operate(client, instance_id, action):
    if action not in {"start", "stop", "status"}:
        raise ValueError("Use start, stop, or status.")
    instance = client.get_instance(instance_id).data
    validate_instance(instance)
    desired = {"start": "RUNNING", "stop": "STOPPED"}.get(action)
    if desired is None:
        return instance, "Server state checked.", False
    if instance.lifecycle_state == desired:
        return instance, "The server is already in the requested state.", False
    expected = "STOPPED" if action == "start" else "RUNNING"
    if instance.lifecycle_state != expected:
        raise ValueError("The server is in transition. Check its status before another action.")
    response = client.instance_action(instance_id, "START" if action == "start" else "SOFTSTOP")
    return response.data, "Server action accepted.", True


def result(instance, message):
    return {
        "state": instance.lifecycle_state,
        "shape": instance.shape,
        "cores": instance.shape_config.ocpus,
        "memory_gb": instance.shape_config.memory_in_gbs,
        "message": message,
        "note": "A running server does not prove the Discord bot is healthy.",
    }


def write_summary(data):
    print(json.dumps(data, indent=2))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        safe_state = re.sub(r"[^A-Z_]", "", data["state"])
        Path(summary).write_text(
            "# Qatro server\n\n"
            f"**Server state: {safe_state}**\n\n"
            f"{data['message']}\n\n"
            "The server uses an Oracle A1 allocation of at most 2 cores and 12 GB RAM.\n\n"
            "Server power state does not prove that Qatro can answer in Discord.\n"
            "A stopped server cannot answer messages.\n",
            encoding="utf-8",
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "stop", "status"])
    parser.add_argument("--no-wait", action="store_true")
    args = parser.parse_args()
    required = ["OCI_TENANCY_OCID", "OCI_USER_OCID", "OCI_FINGERPRINT", "OCI_PRIVATE_KEY", "OCI_REGION", "OCI_INSTANCE_OCID"]
    missing = [name for name in required if not os.environ.get(name, "").strip()]
    if missing:
        parser.error("Missing configuration: " + ", ".join(missing))
    instance_id = os.environ["OCI_INSTANCE_OCID"].strip()
    if not instance_id.startswith("ocid1.instance."):
        parser.error("OCI_INSTANCE_OCID must identify a compute instance.")
    import oci
    config = {
        "tenancy": os.environ["OCI_TENANCY_OCID"].strip(),
        "user": os.environ["OCI_USER_OCID"].strip(),
        "fingerprint": os.environ["OCI_FINGERPRINT"].strip(),
        "key_content": os.environ["OCI_PRIVATE_KEY"],
        "region": os.environ["OCI_REGION"].strip(),
    }
    try:
        oci.config.validate_config(config)
        client = oci.core.ComputeClient(config, timeout=(10, 45))
        instance, message, changed = operate(client, instance_id, args.action)
        if changed and not args.no_wait:
            desired = "RUNNING" if args.action == "start" else "STOPPED"
            instance = oci.wait_until(
                client, client.get_instance(instance_id), "lifecycle_state", desired,
                max_wait_seconds=900, max_interval_seconds=15,
            ).data
            message = "The server reached the requested power state."
        write_summary(result(instance, message))
        return 0
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
    except oci.exceptions.ServiceError as exc:
        print(f"Oracle rejected the request (HTTP {exc.status}). Check the server, capacity, and access settings.", file=sys.stderr)
    except Exception:
        print("The request did not complete. Check Oracle and run the status action before retrying.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
