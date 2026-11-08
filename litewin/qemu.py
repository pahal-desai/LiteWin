import os
import shutil
import subprocess

OVMF_CANDIDATES = [
    ("/usr/share/OVMF/OVMF_CODE_4M.fd", "/usr/share/OVMF/OVMF_VARS_4M.fd"),
    ("/usr/share/OVMF/OVMF_CODE.fd", "/usr/share/OVMF/OVMF_VARS.fd"),
    ("/usr/share/ovmf/OVMF.fd", None),
    ("/usr/share/qemu/OVMF.fd", None),
]


def findovmf():
    for code, vars_file in OVMF_CANDIDATES:
        if os.path.isfile(code):
            return code, vars_file
    return None, None


def makecmd(iso_path, disk_path=None, ram="4G", cpus=4, dry=False):
    if not os.path.isfile(iso_path):
        raise FileNotFoundError(f"ISO file not found: {iso_path}")

    qemu = shutil.which("qemu-system-x86_64")
    if not qemu:
        raise RuntimeError("qemu-system-x86_64 is not installed")

    has_kvm = os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)
    code_fd, vars_fd = findovmf()

    cmd = [qemu]
    if has_kvm:
        cmd.extend(["-enable-kvm", "-cpu", "host"])
    else:
        cmd.extend(["-cpu", "max"])

    cmd.extend([
        "-m", ram,
        "-smp", str(cpus),
        "-vga", "std",
        "-cdrom", iso_path,
        "-boot", "order=d,menu=on",
        "-net", "nic,model=e1000",
        "-net", "user",
    ])

    if code_fd:
        if vars_fd and os.path.isfile(vars_fd):
            cmd.extend([
                "-drive", f"if=pflash,format=raw,readonly=on,file={code_fd}",
            ])
        else:
            cmd.extend(["-bios", code_fd])

    if disk_path:
        cmd.extend(["-drive", f"file={disk_path},format=qcow2,if=virtio"])

    return cmd


def testrun(iso_path, ram="4G", cpus=4, dry=True):
    cmd = makecmd(iso_path, ram=ram, cpus=cpus)
    if dry:
        return {
            "ready": True,
            "command": " ".join(cmd),
            "kvm": os.path.exists("/dev/kvm"),
            "ovmf": findovmf()[0] is not None,
        }

    # launch VM process
    proc = subprocess.Popen(cmd)
    return {
        "ready": True,
        "pid": proc.pid,
        "command": " ".join(cmd),
    }
