import hashlib
import time


def plant_canaries(container, profile_name: str) -> list:
    canary_defs = [
        "/root/.ssh/id_rsa",
        "/home/sandbox/.aws/credentials",
        "/tmp/.canary_token",
        "/etc/canary_secret",
    ]

    manifest = []
    for path in canary_defs:
        token = hashlib.sha256(
            f"{path}{profile_name}{time.time()}".encode()
        ).hexdigest()

        # Create parent directory and plant file
        import pathlib
        parent = str(pathlib.PurePosixPath(path).parent)
        container.exec_run(f"mkdir -p {parent}")
        container.exec_run(f"sh -c 'echo {token} > {path}'")

        manifest.append({
            "path": path,
            "token": token,
            "plant_time": int(time.time()),
        })

    return manifest


def check_canaries(container, manifest: list) -> list:
    triggered = []
    for canary in manifest:
        result = container.exec_run(
            f"stat -c '%X' {canary['path']} 2>/dev/null"
        )
        if result.exit_code != 0:
            continue
        try:
            atime = int(result.output.decode().strip())
            if atime > canary["plant_time"]:
                triggered.append({
                    "path": canary["path"],
                    "accessed_at": atime,
                })
        except ValueError:
            continue
    return triggered