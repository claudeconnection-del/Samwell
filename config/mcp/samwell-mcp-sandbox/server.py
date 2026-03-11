import uuid
import docker
from fastmcp import FastMCP
from profiles import PROFILES
from canary import plant_canaries, check_canaries

mcp = FastMCP("sandbox")
client = docker.from_env()
active_sandboxes: dict = {}


@mcp.tool()
def create_sandbox(profile: str) -> dict:
    """
    Create an ephemeral sandbox container.
    profile: 'code-security' for testing agent-written code,
             'threat-analysis' for quarantined malware analysis.
    Returns sandbox_id to use in subsequent calls.
    """
    if profile not in PROFILES:
        return {"error": f"Unknown profile '{profile}'. Valid: {list(PROFILES.keys())}"}

    p = PROFILES[profile]

    # Install extra packages into a pre-built layer on first use
    container = client.containers.run(
        p.base_image,
        command="sleep infinity",
        detach=True,
        network_mode=p.network_mode,
        mem_limit=p.mem_limit,
        cpu_quota=p.cpu_quota,
        pids_limit=p.pids_limit,
        cap_drop=p.cap_drop,
        cap_add=p.cap_add,
        security_opt=p.security_opt,
        name=f"sandbox-{uuid.uuid4().hex[:8]}",
        labels={"managed-by": "samwell-mcp-sandbox"},
    )

    # Install tooling if profile specifies it
    if p.extra_packages:
        pkgs = " ".join(p.extra_packages)
        container.exec_run(
            f"sh -c 'apt-get update -qq && apt-get install -y -qq {pkgs}'",
            timeout=120,
        )

    canary_manifest = []
    if p.canary_files:
        canary_manifest = plant_canaries(container, profile)

    sandbox_id = container.id[:12]
    active_sandboxes[sandbox_id] = {
        "container": container,
        "profile": profile,
        "canary_manifest": canary_manifest,
    }

    return {
        "sandbox_id": sandbox_id,
        "profile": profile,
        "network": p.network_mode,
        "status": "ready",
    }


@mcp.tool()
def exec_in_sandbox(sandbox_id: str, command: str, timeout: int = 30) -> dict:
    """
    Execute a shell command inside the sandbox.
    Returns stdout, stderr, exit_code, and any canary files that were accessed.
    """
    if sandbox_id not in active_sandboxes:
        return {"error": f"No active sandbox with id '{sandbox_id}'"}

    s = active_sandboxes[sandbox_id]
    result = s["container"].exec_run(
        f"/bin/bash -c '{command}'",
        demux=True,
    )

    stdout = result.output[0].decode() if result.output[0] else ""
    stderr = result.output[1].decode() if result.output[1] else ""
    triggered = check_canaries(s["container"], s["canary_manifest"])

    return {
        "exit_code": result.exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "canaries_triggered": triggered,
    }


@mcp.tool()
def write_file_to_sandbox(sandbox_id: str, path: str, content: str) -> dict:
    """
    Write a file into the sandbox at the given path.
    Use this to transfer code into the sandbox before executing it.
    """
    if sandbox_id not in active_sandboxes:
        return {"error": f"No active sandbox with id '{sandbox_id}'"}

    s = active_sandboxes[sandbox_id]
    import pathlib
    parent = str(pathlib.PurePosixPath(path).parent)
    s["container"].exec_run(f"mkdir -p {parent}")

    # Escape single quotes in content
    escaped = content.replace("'", "'\\''")
    result = s["container"].exec_run(
        f"/bin/bash -c 'cat > {path} << \\'SAMWELL_EOF\\'\\n{escaped}\\nSAMWELL_EOF'"
    )

    return {"path": path, "exit_code": result.exit_code}


@mcp.tool()
def snapshot_sandbox(sandbox_id: str, tag: str) -> dict:
    """
    Commit the current container state as a named snapshot image.
    Only available for the threat-analysis profile.
    Useful for reverting to clean state between malware execution stages.
    """
    if sandbox_id not in active_sandboxes:
        return {"error": f"No active sandbox with id '{sandbox_id}'"}

    s = active_sandboxes[sandbox_id]
    if s["profile"] != "threat-analysis":
        return {"error": "Snapshots are only available for the threat-analysis profile"}

    image = s["container"].commit(repository="samwell-sandbox-snapshot", tag=tag)
    return {"snapshot_id": image.id[:12], "tag": tag}


@mcp.tool()
def destroy_sandbox(sandbox_id: str) -> dict:
    """
    Destroy the sandbox and return a final canary access report.
    Always call this when finished — containers are not auto-cleaned.
    """
    if sandbox_id not in active_sandboxes:
        return {"error": f"No active sandbox with id '{sandbox_id}'"}

    s = active_sandboxes.pop(sandbox_id)
    final_triggered = check_canaries(s["container"], s["canary_manifest"])
    s["container"].remove(force=True)

    return {
        "destroyed": sandbox_id,
        "profile": s["profile"],
        "canaries_triggered": final_triggered,
    }


@mcp.tool()
def list_sandboxes() -> dict:
    """List all currently active sandboxes and their profiles."""
    return {
        sid: {"profile": s["profile"]}
        for sid, s in active_sandboxes.items()
    }


if __name__ == "__main__":
    mcp.run(transport="sse", port=8000, host="0.0.0.0")