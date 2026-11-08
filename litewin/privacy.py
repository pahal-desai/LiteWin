import json
import os

DATADIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def loadprivacy():
    path = os.path.join(DATADIR, "privacy.json")
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def filterprivacy(categories=None):
    items = loadprivacy()
    if not categories:
        return items
    wanted = set(categories)
    return [it for it in items if it.get("category") in wanted]


def makereg(settings):
    # generates .reg file format content
    hives = {}
    for s in settings:
        h = s["hive"]
        if h not in hives:
            hives[h] = []
        hives[h].append(s)

    lines = ["Windows Registry Editor Version 5.00", ""]
    for h, entries in hives.items():
        lines.append(f"[{h}]")
        for e in entries:
            vname = f"\"{e['value']}\""
            if e["type"] == "REG_DWORD":
                val = f"dword:{e['data']:08x}"
            else:
                val = f"\"{e['data']}\""
            lines.append(f"{vname}={val}")
        lines.append("")
    return "\n".join(lines)


def makescript(settings):
    # generates PowerShell script for applying privacy configuration
    lines = [
        "# LiteWin Privacy Configuration Script",
        "$ErrorActionPreference = 'SilentlyContinue'",
        "",
    ]
    for s in settings:
        hive = s["hive"].replace("HKLM\\", "HKLM:\\")
        vname = s["value"]
        kind = "DWord" if s["type"] == "REG_DWORD" else "String"
        val = s["data"]
        desc = s["name"]

        lines.append(f"# {desc}")
        lines.append(
            f"if (!(Test-Path '{hive}')) {{ New-Item -Path '{hive}' -Force | Out-Null }}"
        )
        lines.append(
            f"Set-ItemProperty -Path '{hive}' -Name '{vname}' -Type {kind} -Value {val} -Force"
        )
        lines.append("")
    return "\n".join(lines)
