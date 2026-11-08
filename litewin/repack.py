import os
import shutil
import subprocess

from litewin import iso


def repack(sourcedir, outiso, volid="LITEWIN"):
    if not os.path.isdir(sourcedir):
        raise FileNotFoundError(f"source directory not found: {sourcedir}")

    tool = iso.findtool("xorriso")
    if not tool:
        raise RuntimeError("xorriso is required to generate bootable Windows ISOs")

    os.makedirs(os.path.dirname(os.path.abspath(outiso)), exist_ok=True)

    # detect bootloader files
    bios_boot = os.path.join(sourcedir, "boot", "etfsboot.com")
    uefi_boot = os.path.join(sourcedir, "efi", "microsoft", "boot", "efisys.bin")

    cmd = [
        tool,
        "-as",
        "mkisofs",
        "-iso-level",
        "3",
        "-volid",
        volid,
    ]

    if os.path.isfile(bios_boot):
        cmd.extend([
            "-b",
            "boot/etfsboot.com",
            "-no-emul-boot",
            "-boot-load-size",
            "8",
        ])

    if os.path.isfile(uefi_boot):
        cmd.extend([
            "-eltorito-alt-boot",
            "-e",
            "efi/microsoft/boot/efisys.bin",
            "-no-emul-boot",
        ])

    cmd.extend([
        "-o",
        outiso,
        sourcedir,
    ])

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"xorriso ISO generation failed: {res.stderr or res.stdout}")

    if not os.path.isfile(outiso):
        raise RuntimeError("ISO file was not created by xorriso")

    size = os.path.getsize(outiso)
    return {
        "iso path": outiso,
        "size bytes": size,
        "size mb": round(size / (1024 * 1024), 2),
    }
