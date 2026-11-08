import hashlib
import os
import shutil
import subprocess

# Known official Windows 11 release checksums for validation
KNOWN_HASHES = {
    "bd4307df32bc8af33b39ccecb1174aeb345386630f89a2b86c7a4e36b55ea650": {
        "release": "Windows 11 24H2 / 26100.9457",
        "arch": "x64",
        "language": "en-us",
        "official": True,
    },
}

REQUIRED = [
    "bootmgr",
    "bootmgr.efi",
    "setup.exe",
    "sources/boot.wim",
]


def findtool(name):
    path = shutil.which(name)
    if path:
        return path
    fallback = os.path.expanduser(f"~/.local/bin/{name}")
    if os.path.isfile(fallback) and os.access(fallback, os.X_OK):
        return fallback
    return None


def sha256(path, block=1024 * 1024):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"file not found: {path}")

    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(block):
            hasher.update(chunk)
    return hasher.hexdigest()


def listfiles(iso):
    # inspect archive contents without extracting everything
    seven = findtool("7zz") or findtool("7z")
    if seven:
        res = subprocess.run(
            [seven, "l", iso],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            found = []
            for line in res.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 6 and parts[0].count("-") == 2:
                    name = parts[-1]
                    found.append(name.replace("\\", "/"))
            return found

    # fallback using isoinfo if available
    isoexe = findtool("isoinfo")
    if isoexe:
        res = subprocess.run(
            [isoexe, "-f", "-i", iso],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            return [line.strip().lstrip("/") for line in res.stdout.splitlines() if line.strip()]

    raise RuntimeError("need 7zz, 7z or isoinfo to inspect ISO files")


def verify(iso):
    if not os.path.isfile(iso):
        return {
            "valid": False,
            "error": "ISO file not found",
            "iso path": iso,
        }

    size = os.path.getsize(iso)
    if size < 100 * 1024 * 1024:
        return {
            "valid": False,
            "error": "file too small to be a Windows installation ISO",
            "iso path": iso,
            "size": size,
        }

    entries = listfiles(iso)
    lowers = {e.lower(): e for e in entries}

    missing = []
    for req in REQUIRED:
        if req.lower() not in lowers:
            missing.append(req)

    haswim = "sources/install.wim" in lowers
    hasesd = "sources/install.esd" in lowers

    if not haswim and not hasesd:
        missing.append("sources/install.wim or sources/install.esd")

    valid = len(missing) == 0
    imgtype = "wim" if haswim else ("esd" if hasesd else "unknown")
    imgfile = lowers.get("sources/install.wim") or lowers.get("sources/install.esd")

    return {
        "valid": valid,
        "iso path": iso,
        "size": size,
        "mb": round(size / (1024 * 1024), 2),
        "total files": len(entries),
        "image type": imgtype,
        "image file": imgfile,
        "missing files": missing,
    }


def inspect(iso, checkhash=False):
    # combines fast validation with optional hash verification
    info = verify(iso)
    if not info.get("valid"):
        return info

    if checkhash:
        digest = sha256(iso)
        info["sha256"] = digest
        match = KNOWN_HASHES.get(digest)
        if match:
            info["official release"] = match["release"]
            info["architecture"] = match["arch"]
            info["language"] = match["language"]
        else:
            info["official release"] = "custom or unverified"

    return info


def extract(iso, dest, picks=None):
    # extracts files safely into dest without touching the original ISO
    if not os.path.isfile(iso):
        raise FileNotFoundError(f"ISO not found: {iso}")

    os.makedirs(dest, exist_ok=True)
    seven = findtool("7zz") or findtool("7z")
    if not seven:
        raise RuntimeError("7zz or 7z is required for safe ISO extraction")

    cmd = [seven, "x", "-y", f"-o{dest}", iso]
    if picks:
        cmd.extend(picks)

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"extraction failed: {res.stderr or res.stdout}")

    return dest
