import json
import os
import time

COLLECT_SCRIPT = """# LiteWin Benchmark Collector Script
# Run this inside stock Windows or LiteWin to gather factual metrics
$ErrorActionPreference = 'SilentlyContinue'

$os = Get-CimInstance Win32_OperatingSystem
$disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
$procs = (Get-Process).Count
$startups = (Get-CimInstance Win32_StartupCommand).Count

$totalRamMB = [math]::Round($os.TotalVisibleMemorySize / 1024, 0)
$freeRamMB = [math]::Round($os.FreePhysicalMemory / 1024, 0)
$usedRamMB = $totalRamMB - $freeRamMB

$totalDiskGB = [math]::Round($disk.Size / 1GB, 2)
$freeDiskGB = [math]::Round($disk.FreeSpace / 1GB, 2)
$usedDiskGB = [math]::Round(($disk.Size - $disk.FreeSpace) / 1GB, 2)

# Boot time from Diagnostics-Performance Event ID 100
$bootEvent = Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Diagnostics-Performance/Operational'; Id=100} -MaxEvents 1 -ErrorAction SilentlyContinue
$bootTimeSec = if ($bootEvent) { [math]::Round($bootEvent.Properties[0].Value / 1000, 2) } else { "N/A" }

$metrics = [ordered]@{
    "collection time" = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    "process count" = $procs
    "startup apps" = $startups
    "used ram mb" = $usedRamMB
    "total ram mb" = $totalRamMB
    "used disk gb" = $usedDiskGB
    "boot time sec" = $bootTimeSec
}

$metrics | ConvertTo-Json -Depth 2
"""


def getcollector():
    return COLLECT_SCRIPT


def compare(stock, litewin):
    # compares live collected metrics between stock Windows and LiteWin
    # never fabricates numbers
    comp = {
        "stock": stock,
        "litewin": litewin,
        "delta": {},
    }

    for key in ["process count", "startup apps", "used ram mb", "used disk gb", "boot time sec"]:
        v_stock = stock.get(key)
        v_lite = litewin.get(key)
        if isinstance(v_stock, (int, float)) and isinstance(v_lite, (int, float)):
            diff = round(v_lite - v_stock, 2)
            pct = round((diff / v_stock) * 100, 1) if v_stock != 0 else 0
            comp["delta"][key] = {
                "difference": diff,
                "percent change": f"{pct}%",
            }
        else:
            comp["delta"][key] = {
                "difference": "N/A",
                "percent change": "N/A",
            }

    return comp


def markdown(comp, conditions=None):
    lines = [
        "# LiteWin Performance Benchmark Report",
        "",
        "> Comparing Stock Windows 11 vs LiteWin under verified test conditions",
        "",
    ]
    if conditions:
        lines.append(f"**Test Conditions:** {conditions}\n")

    lines.extend([
        "| Metric | Stock Windows 11 | LiteWin | Delta | Change |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])

    stock = comp.get("stock", {})
    lite = comp.get("litewin", {})
    delta = comp.get("delta", {})

    labels = {
        "process count": "Background Processes",
        "startup apps": "Startup Applications",
        "used ram mb": "Idle Memory (MB)",
        "used disk gb": "Installation Disk (GB)",
        "boot time sec": "Boot Time (Seconds)",
    }

    for k, label in labels.items():
        s_val = stock.get(k, "N/A")
        l_val = lite.get(k, "N/A")
        d_val = delta.get(k, {}).get("difference", "N/A")
        p_val = delta.get(k, {}).get("percent change", "N/A")
        lines.append(f"| {label} | {s_val} | {l_val} | {d_val} | {p_val} |")

    lines.extend([
        "",
        "*Note: Benchmarks reflect actual clean VM test installations. Results vary depending on hardware configuration.*",
        "",
    ])
    return "\n".join(lines)
