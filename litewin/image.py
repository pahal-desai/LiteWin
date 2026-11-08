import os
import platform
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET

from litewin import iso

ARCH_MAP = {
    0: "x86",
    5: "arm",
    9: "x64",
    12: "arm64",
}


def findtool(name):
    return iso.findtool(name)


def detectenv():
    # identify available image servicing tools on the host
    sysname = platform.system().lower()
    hasdism = shutil.which("dism.exe") or shutil.which("dism")
    haswimlib = findtool("wimlib-imagex") or findtool("wiminfo")

    if sysname == "windows" and hasdism:
        return {"environment": "windows", "engine": "dism", "supported": True}
    if haswimlib:
        return {"environment": sysname, "engine": "wimlib", "supported": True}
    return {
        "environment": sysname,
        "engine": "none",
        "supported": False,
        "note": "neither DISM nor wimlib-imagex was found",
    }


def parsexml(xmltext):
    clean = xmltext.lstrip("\ufeff").strip()
    root = ET.fromstring(clean)
    items = []
    for img in root.findall("IMAGE"):
        idx = int(img.attrib.get("INDEX", "1"))
        name = img.findtext("NAME") or f"Image {idx}"
        desc = img.findtext("DESCRIPTION") or ""
        bytesize = int(img.findtext("TOTALBYTES") or 0)

        win = img.find("WINDOWS")
        arch_id = 9
        edition_id = "Windows"
        install_type = "Client"
        build = "unknown"
        sp = "0"
        lang = "en-US"

        if win is not None:
            raw_arch = win.findtext("ARCH")
            if raw_arch and raw_arch.isdigit():
                arch_id = int(raw_arch)
            edition_id = win.findtext("EDITIONID") or edition_id
            install_type = win.findtext("INSTALLATIONTYPE") or install_type
            langs = win.find("LANGUAGES")
            if langs is not None:
                lang = langs.findtext("DEFAULT") or lang
            ver = win.find("VERSION")
            if ver is not None:
                build = ver.findtext("BUILD") or build
                sp = ver.findtext("SPBUILD") or sp

        fullver = f"{build}.{sp}" if sp != "0" else build
        items.append({
            "index": idx,
            "name": name,
            "description": desc,
            "edition": edition_id,
            "type": install_type,
            "architecture": ARCH_MAP.get(arch_id, f"unknown-{arch_id}"),
            "build": fullver,
            "language": lang,
            "size bytes": bytesize,
            "size mb": round(bytesize / (1024 * 1024), 2),
        })
    return items


def readwimxml(path, offset=0):
    with open(path, "rb") as f:
        f.seek(offset)
        hdr = f.read(208)
        if len(hdr) < 208 or hdr[:8] != b"MSWIM\x00\x00\x00":
            return None

        # XML reshdr is at offset 0x48 (24 bytes)
        xmlres = hdr[0x48:0x60]
        xml_offset = struct.unpack("<Q", xmlres[8:16])[0]
        xml_size = struct.unpack("<Q", xmlres[16:24])[0]

        f.seek(offset + xml_offset)
        raw = f.read(xml_size)
        return raw.decode("utf-16le", errors="replace")


def findwims(path, maxscan=2 * 1024 * 1024 * 1024):
    # scans a file (like an ISO) for embedded MSWIM images
    found = []
    with open(path, "rb") as f:
        step = 32 * 1024 * 1024
        curr = 0
        while curr < maxscan:
            chunk = f.read(step)
            if not chunk:
                break
            pos = 0
            while True:
                pos = chunk.find(b"MSWIM\x00\x00\x00", pos)
                if pos == -1:
                    break
                abs_offset = curr + pos
                if abs_offset % 2048 == 0:
                    xml = readwimxml(path, abs_offset)
                    if xml:
                        items = parsexml(xml)
                        found.append({
                            "offset": abs_offset,
                            "count": len(items),
                            "items": items,
                        })
                        # if we found the install image with full Windows editions, we can stop
                        is_install = any(
                            "pe" not in item["type"].lower() and "pe" not in item["name"].lower()
                            for item in items
                        )
                        if is_install:
                            return found
                pos += 8
            curr += len(chunk)
    return found


def editions(target, role="install"):
    if not os.path.isfile(target):
        raise FileNotFoundError(f"image target not found: {target}")

    # check if target itself is a WIM
    with open(target, "rb") as f:
        magic = f.read(8)
    if magic == b"MSWIM\x00\x00\x00":
        text = readwimxml(target, 0)
        if text:
            return parsexml(text)

    # if target is an ISO, look for the install image inside
    wims = findwims(target)
    if not wims:
        wimtool = findtool("wiminfo")
        if wimtool:
            res = subprocess.run([wimtool, "--xml", target], capture_output=True, text=False)
            if res.returncode == 0:
                text = res.stdout.decode("utf-16le", errors="replace")
                return parsexml(text)
        raise RuntimeError(f"could not read Windows image metadata from {target}")

    if role == "install":
        # pick the WIM that has full Windows installations (not just Windows PE)
        for w in wims:
            for item in w["items"]:
                if "pe" not in item["type"].lower() and "pe" not in item["name"].lower():
                    return w["items"]
        # fallback to the WIM with the most images
        wims.sort(key=lambda x: x["count"], reverse=True)
        return wims[0]["items"]

    if role == "boot":
        # pick PE bootloader WIM
        for w in wims:
            for item in w["items"]:
                if "pe" in item["type"].lower() or "pe" in item["name"].lower():
                    return w["items"]

    return wims[0]["items"]



def export(src, idx, dest, name=None):
    # exports a single edition from a multi-edition WIM into a new clean WIM
    tool = findtool("wimexport")
    if not tool:
        raise RuntimeError("wimexport is required to export image editions")

    cmd = [tool, src, str(idx), dest]
    if name:
        cmd.extend(["--dest-name", name])

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"wimexport failed: {res.stderr or res.stdout}")

    return dest


def makescript(mountdir, packages=None, registry=None):
    # generates a standalone PowerShell / DISM script that can be delegated to Windows
    lines = [
        "# LiteWin Servicing Script",
        "# Generated for Windows DISM delegation",
        "$ErrorActionPreference = 'Stop'",
        f"$MountDir = '{mountdir}'",
        "",
    ]

    if packages:
        lines.append("# Removing selected provisioned app packages")
        for pkg in packages:
            lines.append(
                f"Get-AppxProvisionedPackage -Path $MountDir | "
                f"Where-Object {{ $_.DisplayName -like '*{pkg}*' }} | "
                f"Remove-AppxProvisionedPackage -Path $MountDir"
            )
        lines.append("")

    if registry:
        lines.append("# Applying privacy registry settings")
        lines.append("reg load HKLM\\LiteWinDefault $MountDir\\Windows\\System32\\config\\default")
        lines.append("reg load HKLM\\LiteWinSoftware $MountDir\\Windows\\System32\\config\\SOFTWARE")
        for reg in registry:
            hive = reg.get("hive", "HKLM\\LiteWinSoftware")
            key = reg.get("key")
            val = reg.get("value")
            kind = reg.get("type", "REG_DWORD")
            data = reg.get("data")
            lines.append(f"reg add \"{hive}\\{key}\" /v \"{val}\" /t {kind} /d {data} /f")
        lines.append("reg unload HKLM\\LiteWinSoftware")
        lines.append("reg unload HKLM\\LiteWinDefault")
        lines.append("")

    return "\n".join(lines)
