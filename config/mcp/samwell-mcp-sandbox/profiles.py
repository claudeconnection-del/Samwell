from dataclasses import dataclass, field

@dataclass
class SandboxProfile:
    base_image: str
    network_mode: str
    mem_limit: str
    cpu_quota: int
    pids_limit: int
    cap_drop: list
    cap_add: list
    security_opt: list
    canary_files: bool
    syscall_trace: bool
    extra_packages: list = field(default_factory=list)

PROFILES = {
    "code-security": SandboxProfile(
        base_image="ubuntu:24.04",
        network_mode="bridge",
        mem_limit="512m",
        cpu_quota=50000,
        pids_limit=128,
        cap_drop=["ALL"],
        cap_add=["NET_BIND_SERVICE"],
        security_opt=["no-new-privileges:true"],
        canary_files=True,
        syscall_trace=False,
        extra_packages=["python3-pip", "nodejs", "npm", "semgrep", "binutils"],
    ),
    "threat-analysis": SandboxProfile(
        base_image="ubuntu:24.04",
        network_mode="none",
        mem_limit="1g",
        cpu_quota=25000,
        pids_limit=64,
        cap_drop=["ALL"],
        cap_add=[],
        security_opt=["no-new-privileges:true"],
        canary_files=True,
        syscall_trace=True,
        extra_packages=["strace", "ltrace", "binutils", "file"],
    ),
}