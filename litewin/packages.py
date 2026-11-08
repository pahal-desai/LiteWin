import json
import os

DATADIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def loadapps():
    path = os.path.join(DATADIR, "apps.json")
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def filterapps(profile="standard", custom=None):
    allapps = loadapps()
    removals = []
    retained = []

    if profile == "minimal":
        # removes only the most obvious spam and ads
        targets = {
            "Clipchamp.Clipchamp",
            "Microsoft.BingNews",
            "Microsoft.MicrosoftSolitaireCollection",
            "Microsoft.MicrosoftOfficeHub",
            "Microsoft.Getstarted",
            "Microsoft.549981C3F5F10",
        }
        for a in allapps:
            if a["id"] in targets and a.get("safe to remove"):
                removals.append(a)
            else:
                retained.append(a)

    elif profile == "standard":
        # removes non-essential bloat, keeps system and essential tools
        for a in allapps:
            if a.get("safe to remove"):
                removals.append(a)
            else:
                retained.append(a)

    elif profile == "custom" and custom:
        wanted = set(custom)
        for a in allapps:
            if a["id"] in wanted:
                if not a.get("safe to remove"):
                    raise ValueError(
                        f"cannot remove essential package {a['name']} ({a['id']}): {a.get('reason')}"
                    )
                removals.append(a)
            else:
                retained.append(a)
    else:
        # fallback to standard
        return filterapps(profile="standard")

    return {
        "profile": profile,
        "remove": removals,
        "retain": retained,
    }


def makescript(removals):
    # generates PowerShell removal lines that can be run offline or during setup
    lines = [
        "# LiteWin Package Removal Script",
        "$ErrorActionPreference = 'SilentlyContinue'",
    ]
    for app in removals:
        pkg_id = app["id"]
        name = app.get("name", pkg_id)
        lines.append(f"# Remove {name}")
        lines.append(
            f"Get-AppxProvisionedPackage -Online | Where-Object {{ $_.DisplayName -like '*{pkg_id}*' }} | "
            f"Remove-AppxProvisionedPackage -Online"
        )
        lines.append(
            f"Get-AppxPackage -AllUsers -Name '*{pkg_id}*' | Remove-AppxPackage -AllUsers"
        )
    return "\n".join(lines)
