#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

/*
 * LiteWin Windows Bootstrapper Executable
 * Automatically checks for Python, installs it if not found,
 * ensures dependencies are ready, and launches the LiteWin GUI.
 */

int check_python(void) {
    // Try running python --version
    int ret = system("python --version >nul 2>&1");
    if (ret == 0) return 1;

    // Try running py --version
    ret = system("py -3 --version >nul 2>&1");
    if (ret == 0) return 2;

    return 0;
}

int install_python(void) {
    printf("[LiteWin] Python 3 was not detected on this machine.\n");
    printf("[LiteWin] Automatically installing Python 3 for Windows...\n");

    // Method 1: Try winget first if available
    int ret = system("winget --version >nul 2>&1");
    if (ret == 0) {
        printf("[LiteWin] Installing Python via Windows Package Manager (winget)...\n");
        ret = system("winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements");
        if (ret == 0) {
            printf("[LiteWin] Python installed successfully via winget.\n");
            return 1;
        }
    }

    // Method 2: Download official python installer using PowerShell
    printf("[LiteWin] Downloading official Python 3.12 installer from python.org...\n");
    const char *ps_cmd =
        "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \""
        "$url = 'https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe'; "
        "$dest = '$env:TEMP\\python_installer.exe'; "
        "Write-Host '[LiteWin] Downloading Python...'; "
        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; "
        "(New-Object System.Net.WebClient).DownloadFile($url, $dest); "
        "Write-Host '[LiteWin] Running silent Python installation...'; "
        "Start-Process -FilePath $dest -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_test=0' -Wait; "
        "Remove-Item -Path $dest -Force -ErrorAction SilentlyContinue; "
        "\"";

    ret = system(ps_cmd);
    if (ret == 0) {
        printf("[LiteWin] Python installation completed.\n");
        return 1;
    }

    printf("[LiteWin] Error: Failed to automatically install Python. Please install Python from https://python.org\n");
    return 0;
}

void install_deps(const char *py_cmd) {
    char cmd[512];
    printf("[LiteWin] Verifying LiteWin dependencies...\n");
    snprintf(cmd, sizeof(cmd), "%s -m pip install -e . --quiet", py_cmd);
    system(cmd);
}

int main(int argc, char *argv[]) {
    printf("====================================================\n");
    printf(" LiteWin - Windows, without the baggage.\n");
    printf(" Windows Native Launcher\n");
    printf("====================================================\n\n");

    int py_status = check_python();
    if (!py_status) {
        if (!install_python()) {
            printf("\nPress any key to exit...\n");
            getchar();
            return 1;
        }
        py_status = check_python();
    }

    const char *py_cmd = (py_status == 2) ? "py -3" : "python";
    install_deps(py_cmd);

    printf("[LiteWin] Launching LiteWin Graphical User Interface...\n");
    char run_cmd[1024];
    snprintf(run_cmd, sizeof(run_cmd), "%s -m litewin.cli gui", py_cmd);

    // If arguments were passed to litewin.exe, pass them through
    if (argc > 1) {
        char args_buf[1024] = {0};
        for (int i = 1; i < argc; i++) {
            strncat(args_buf, " ", sizeof(args_buf) - strlen(args_buf) - 1);
            strncat(args_buf, argv[i], sizeof(args_buf) - strlen(args_buf) - 1);
        }
        snprintf(run_cmd, sizeof(run_cmd), "%s -m litewin.cli %s", py_cmd, args_buf);
    }

    return system(run_cmd);
}
