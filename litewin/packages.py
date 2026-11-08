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
        "",
    ]
    for app in removals:
        pkg_id = app["id"]
        name = app.get("name", pkg_id)

        if pkg_id == "Microsoft-Edge":
            lines.extend([
                f"# Remove {name} (Strictly preserving WebView2 runtime)",
                "$edgeSetup = Get-ChildItem -Path \"${env:ProgramFiles(x86)}\\Microsoft\\Edge\\Application\" -Filter \"setup.exe\" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1",
                "if ($edgeSetup) {",
                "    Start-Process -FilePath $edgeSetup.FullName -ArgumentList \"--uninstall --system-level --verbose-logging --force-uninstall\" -Wait -WindowStyle Hidden",
                "}",
                "Get-AppxPackage -AllUsers -Name \"*MicrosoftEdge*\" | Where-Object { $_.Name -notlike \"*WebView*\" } | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue",
                "Get-AppxProvisionedPackage -Online | Where-Object { $_.DisplayName -like \"*MicrosoftEdge*\" -and $_.DisplayName -notlike \"*WebView*\" } | Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue",
                "",
            ])
        elif pkg_id == "WindowsDefender":
            lines.extend([
                f"# Completely Eradicate {name} and Antimalware Service Executable (MsMpEng.exe)",
                "# 1. Terminate running antimalware processes",
                "Get-Process -Name 'MsMpEng', 'NisSrv', 'SecurityHealthService', 'SecurityHealthSystray' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue",
                "",
                "# 2. Disable real-time and behavior monitoring preferences",
                "Set-MpPreference -DisableRealtimeMonitoring $true -ErrorAction SilentlyContinue",
                "Set-MpPreference -DisableBehaviorMonitoring $true -ErrorAction SilentlyContinue",
                "Set-MpPreference -DisableIOAVProtection $true -ErrorAction SilentlyContinue",
                "Set-MpPreference -DisableScriptScanning $true -ErrorAction SilentlyContinue",
                "Set-MpPreference -SubmitSamplesConsent 2 -ErrorAction SilentlyContinue",
                "Set-MpPreference -MAPSReporting 0 -ErrorAction SilentlyContinue",
                "",
                "# 3. Set policy registry locks",
                "reg add \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender\" /v DisableAntiSpyware /t REG_DWORD /d 1 /f",
                "reg add \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender\" /v DisableRealtimeMonitoring /t REG_DWORD /d 1 /f",
                "reg add \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender\\Real-Time Protection\" /v DisableBehaviorMonitoring /t REG_DWORD /d 1 /f",
                "reg add \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender\\Real-Time Protection\" /v DisableOnAccessProtection /t REG_DWORD /d 1 /f",
                "reg add \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender\\Real-Time Protection\" /v DisableScanOnRealtimeEnable /t REG_DWORD /d 1 /f",
                "reg add \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender\\Real-Time Protection\" /v DisableIOAVProtection /t REG_DWORD /d 1 /f",
                "",
                "# 4. Unregister Defender scheduled tasks",
                "Get-ScheduledTask -TaskPath \"\\Microsoft\\Windows\\Windows Defender\\*\" -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false -ErrorAction SilentlyContinue",
                "",
                "# 5. Stop and delete Defender services and filter drivers",
                "$defServices = @('WinDefend', 'WdNisSvc', 'WdFilter', 'WdNisDrv', 'Sense', 'SecurityHealthService')",
                "foreach ($svc in $defServices) {",
                "    Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue",
                "    sc.exe delete $svc | Out-Null",
                "}",
                "",
                "# 6. Delete Defender binaries including MsMpEng.exe (Antimalware Service Executable)",
                "$defPaths = @(",
                "    \"${env:ProgramFiles}\\Windows Defender\",",
                "    \"${env:ProgramFiles(x86)}\\Windows Defender\",",
                "    \"${env:ProgramData}\\Microsoft\\Windows Defender\",",
                "    \"${env:ProgramData}\\Microsoft\\Windows Defender Advanced Threat Protection\"",
                ")",
                "foreach ($p in $defPaths) {",
                "    if (Test-Path $p) {",
                "        takeown.exe /f $p /r /d y | Out-Null",
                "        icacls.exe $p /grant \"Administrators:F\" /t /c /q | Out-Null",
                "        Remove-Item -Path $p -Recurse -Force -ErrorAction SilentlyContinue",
                "    }",
                "}",
                "",
                "# 7. Delete Defender service registry trees",
                "$defRegs = @(",
                "    'HKLM:\\SOFTWARE\\Microsoft\\Windows Defender',",
                "    'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\WinDefend',",
                "    'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\WdNisSvc',",
                "    'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\WdFilter',",
                "    'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\WdNisDrv',",
                "    'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Sense',",
                "    'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\SecurityHealthService'",
                ")",
                "foreach ($r in $defRegs) {",
                "    Remove-Item -Path $r -Recurse -Force -ErrorAction SilentlyContinue",
                "}",
                "",
                "# 8. Remove Windows Security dashboard Appx",
                "Get-AppxPackage -AllUsers -Name \"*SecHealthUI*\" | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue",
                "Get-AppxProvisionedPackage -Online | Where-Object { $_.DisplayName -like \"*SecHealthUI*\" } | Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue",
                "",
            ])
        else:
            lines.extend([
                f"# Remove {name}",
                f"Get-AppxProvisionedPackage -Online | Where-Object {{ $_.DisplayName -like '*{pkg_id}*' }} | Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue",
                f"Get-AppxPackage -AllUsers -Name '*{pkg_id}*' | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue",
                "",
            ])

    return "\n".join(lines)
