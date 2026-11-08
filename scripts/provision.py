"""Plan or create one Oracle A1 server within this project's free allocation limits."""
from __future__ import annotations
import argparse
import base64
import ipaddress
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".private/oci-state.json"
SHAPE = "VM.Standard.A1.Flex"
TAGS = {"qatro-managed": "true"}


def check_allowance(instances, disk_gb):
    active = [x for x in instances if x.lifecycle_state not in {"TERMINATED", "TERMINATING"}]
    cores = sum(x.shape_config.ocpus for x in active if x.shape == SHAPE)
    memory = sum(x.shape_config.memory_in_gbs for x in active if x.shape == SHAPE)
    if cores != 0 or memory != 0:
        raise ValueError("This account already has A1 resources. Review the account allocation before creating Qatro.")
    if disk_gb + 50 > 200:
        raise ValueError("A new 50 GB disk would exceed the account's 200 GB free disk allowance.")
    return {"cores": 2, "memory_gb": 12, "boot_disk_gb": 50, "existing_disk_gb": disk_gb}


def cloud_init():
    def file(path, text, permissions):
        return {"path": path, "permissions": permissions, "owner": "root:root", "content": text}
    return "#cloud-config\n" + json.dumps({
        "users": ["default", {"name": "qatro", "shell": "/bin/bash", "lock_passwd": True}],
        "package_update": True,
        "packages": ["curl", "git", "ca-certificates", "unzip", "python3"],
        "write_files": [
            file("/opt/qatro-setup/bootstrap.sh", (ROOT / "cloud/bootstrap.sh").read_text(encoding="utf-8"), "0755"),
            file("/etc/systemd/system/qatro.service", (ROOT / "cloud/qatro.service").read_text(encoding="utf-8"), "0644"),
        ],
        "runcmd": [["runuser", "-u", "qatro", "--", "/opt/qatro-setup/bootstrap.sh"], ["systemctl", "daemon-reload"]],
    })


def inventory(oci, config, identity, compute, network, block, compartment):
    all_results = oci.pagination.list_call_get_all_results
    regions = identity.list_region_subscriptions(config["tenancy"]).data
    home = next((r.region_name for r in regions if r.is_home_region), None)
    if config["region"] != home:
        raise ValueError("Select the tenancy's home region before provisioning free resources.")
    children = all_results(identity.list_compartments, config["tenancy"], compartment_id_in_subtree=True, access_level="ANY").data
    compartments = {config["tenancy"], *(c.id for c in children if c.lifecycle_state == "ACTIVE")}
    if compartment not in compartments:
        raise ValueError("The selected compartment is not active in this tenancy.")
    ads = identity.list_availability_domains(config["tenancy"]).data
    instances, disk_gb = [], 0
    for cid in compartments:
        instances.extend(all_results(compute.list_instances, compartment_id=cid).data)
        volumes = all_results(block.list_volumes, compartment_id=cid).data
        disk_gb += sum(v.size_in_gbs for v in volumes if v.lifecycle_state != "TERMINATED")
        for ad in ads:
            boots = all_results(block.list_boot_volumes, compartment_id=cid, availability_domain=ad.name).data
            disk_gb += sum(v.size_in_gbs for v in boots if v.lifecycle_state != "TERMINATED")
    limits = check_allowance(instances, disk_gb)
    images = all_results(compute.list_images, compartment_id=compartment, operating_system="Canonical Ubuntu", operating_system_version="24.04", shape=SHAPE, sort_by="TIMECREATED", sort_order="DESC").data
    images = [i for i in images if i.lifecycle_state == "AVAILABLE" and "aarch64" in i.display_name.lower()]
    if not images: raise ValueError("No compatible Ubuntu ARM image is available in this region.")
    supported_ads = []
    for ad in ads:
        shapes = all_results(compute.list_shapes, compartment_id=compartment, availability_domain=ad.name, image_id=images[0].id).data
        if any(s.shape == SHAPE for s in shapes): supported_ads.append(ad.name)
    if not supported_ads: raise ValueError("No availability domain offers the required A1 shape.")
    return {"region": home, "compartment": compartment, "image": images[0].id, "availability_domain": supported_ads[0], "limits": limits}


def create(oci, compute, network, plan, ssh_key, admin_cidr):
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"region": plan["region"], "compartment": plan["compartment"]}
    if state["region"] != plan["region"] or state["compartment"] != plan["compartment"]:
        raise ValueError("The saved deployment belongs to a different region or compartment.")
    cid = plan["compartment"]

    def save(key, identifier):
        state[key] = identifier
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        STATE.chmod(0o600)
        return identifier

    def resource(key, make):
        return state.get(key) or save(key, make().data.id)

    m = oci.core.models
    vcn = resource("vcn", lambda: network.create_vcn(m.CreateVcnDetails(compartment_id=cid, cidr_block="10.42.0.0/16", display_name="qatro-cloud", dns_label="qatro", freeform_tags=TAGS)))
    oci.wait_until(network, network.get_vcn(vcn), "lifecycle_state", "AVAILABLE", max_wait_seconds=180)
    gateway = resource("internet_gateway", lambda: network.create_internet_gateway(m.CreateInternetGatewayDetails(compartment_id=cid, vcn_id=vcn, is_enabled=True, display_name="qatro-cloud", freeform_tags=TAGS)))
    route = resource("route_table", lambda: network.create_route_table(m.CreateRouteTableDetails(compartment_id=cid, vcn_id=vcn, display_name="qatro-cloud", freeform_tags=TAGS, route_rules=[m.RouteRule(destination="0.0.0.0/0", destination_type="CIDR_BLOCK", network_entity_id=gateway)])))
    security = resource("security_list", lambda: network.create_security_list(m.CreateSecurityListDetails(
        compartment_id=cid, vcn_id=vcn, display_name="qatro-cloud", freeform_tags=TAGS,
        ingress_security_rules=[m.IngressSecurityRule(protocol="6", source=admin_cidr, tcp_options=m.TcpOptions(destination_port_range=m.PortRange(min=22, max=22)))],
        egress_security_rules=[m.EgressSecurityRule(protocol="all", destination="0.0.0.0/0")],
    )))
    subnet = resource("subnet", lambda: network.create_subnet(m.CreateSubnetDetails(compartment_id=cid, vcn_id=vcn, cidr_block="10.42.1.0/24", display_name="qatro-cloud", dns_label="qatro", route_table_id=route, security_list_ids=[security], freeform_tags=TAGS)))
    oci.wait_until(network, network.get_subnet(subnet), "lifecycle_state", "AVAILABLE", max_wait_seconds=180)
    if "instance" in state:
        raise ValueError("A Qatro instance is already recorded. Use its control actions instead of creating another.")
    details = m.LaunchInstanceDetails(
        compartment_id=cid, availability_domain=plan["availability_domain"], display_name="qatro",
        shape=SHAPE, shape_config=m.LaunchInstanceShapeConfigDetails(ocpus=2, memory_in_gbs=12),
        create_vnic_details=m.CreateVnicDetails(subnet_id=subnet, assign_public_ip=True, display_name="qatro"),
        source_details=m.InstanceSourceViaImageDetails(image_id=plan["image"], boot_volume_size_in_gbs=50),
        metadata={"ssh_authorized_keys": ssh_key, "user_data": base64.b64encode(cloud_init().encode()).decode()},
        freeform_tags=TAGS,
    )
    response = compute.launch_instance(details, opc_retry_token="qatro-" + state["vcn"].split(".")[-1][:48])
    save("instance", response.data.id)
    print("Qatro's server was created. The gateway remains stopped until its private state is migrated.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile", default="DEFAULT")
    p.add_argument("--compartment", required=True)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--ssh-public-key", type=Path)
    p.add_argument("--admin-cidr")
    a = p.parse_args()
    import oci
    try:
        config = oci.config.from_file(profile_name=a.profile)
        identity, compute, network, block = oci.identity.IdentityClient(config), oci.core.ComputeClient(config), oci.core.VirtualNetworkClient(config), oci.core.BlockstorageClient(config)
        plan = inventory(oci, config, identity, compute, network, block, a.compartment)
        print(json.dumps({"region": plan["region"], "server": plan["limits"], "apply": a.apply}, indent=2))
        if not a.apply: return 0
        if not a.ssh_public_key or not a.admin_cidr: raise ValueError("Supply an SSH public key and a single administrator IPv4 address with /32.")
        admin = ipaddress.ip_network(a.admin_cidr, strict=True)
        if admin.version != 4 or admin.prefixlen != 32: raise ValueError("SSH access must use one administrator IPv4 address with /32.")
        key = a.ssh_public_key.read_text(encoding="utf-8").strip()
        if not key.startswith(("ssh-ed25519 ", "ssh-rsa ", "ecdsa-sha2-")): raise ValueError("Supply a public SSH key, not a private key.")
        create(oci, compute, network, plan, key, str(admin))
        return 0
    except ValueError as exc: print(str(exc), file=sys.stderr)
    except oci.exceptions.ServiceError as exc: print(f"Oracle could not complete the request (HTTP {exc.status}). No paid fallback will run.", file=sys.stderr)
    except Exception: print("Provisioning stopped. Review Oracle and the saved deployment state before retrying.", file=sys.stderr)
    return 1


if __name__ == "__main__": raise SystemExit(main())
