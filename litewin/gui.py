import ctypes
import os
import queue
import sys
import threading
import time


def init_tk():
    # dynamically configure standalone tcl/tk libraries if needed on Linux
    tcl_dir = os.path.expanduser("~/.local/usr/share/tcltk/tcl8.6")
    tk_dir = os.path.expanduser("~/.local/usr/share/tcltk/tk8.6")
    if os.path.isdir(tcl_dir):
        os.environ["TCL_LIBRARY"] = tcl_dir
    if os.path.isdir(tk_dir):
        os.environ["TK_LIBRARY"] = tk_dir

    sys.path.append(os.path.expanduser("~/.local/usr/lib/python3.12"))
    sys.path.append(os.path.expanduser("~/.local/usr/lib/python3.12/lib-dynload"))

    libs = [
        os.path.expanduser("~/.local/usr/lib/x86_64-linux-gnu/libtcl8.6.so"),
        os.path.expanduser("~/.local/usr/lib/x86_64-linux-gnu/libtk8.6.so"),
        os.path.expanduser("~/.local/usr/lib/libBLT.2.5.so.8.6"),
    ]
    for lib in libs:
        if os.path.isfile(lib):
            try:
                ctypes.CDLL(lib, mode=ctypes.RTLD_GLOBAL)
            except Exception:
                pass


init_tk()

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from litewin import iso
from litewin import image
from litewin import packages
from litewin import privacy
from litewin import builder
from litewin import qemu
from litewin import version


class GuiApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"LiteWin v{version} — Windows, without the baggage")
        self.root.geometry("860x680")
        self.root.minsize(760, 580)

        # state variables
        self.iso_path = tk.StringVar()
        self.out_iso_path = tk.StringVar()
        self.edition_var = tk.StringVar()
        self.username_var = tk.StringVar(value="User")
        self.profile_var = tk.StringVar(value="standard")
        self.single_edition_var = tk.BooleanVar(value=False)
        self.firefox_var = tk.BooleanVar(value=True)

        self.detected_editions = []
        self.app_checks = {}
        self.privacy_checks = {}
        self.log_queue = queue.Queue()
        self.build_active = False

        self.setup_ui()
        self.root.after(100, self.process_logs)

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Top banner
        header = ttk.Frame(self.root, padding="12 10")
        header.pack(fill=tk.X)
        title = ttk.Label(header, text="LiteWin", font=("Helvetica", 18, "bold"))
        title.pack(side=tk.LEFT)
        tagline = ttk.Label(
            header,
            text=" — Windows, without the baggage.",
            font=("Helvetica", 11, "italic"),
        )
        tagline.pack(side=tk.LEFT, pady=4)

        ver = ttk.Label(header, text=f"v{version}", font=("Helvetica", 10))
        ver.pack(side=tk.RIGHT, pady=4)

        # ISO selection frame
        src_frame = ttk.LabelFrame(self.root, text="Source Windows 11 ISO", padding=10)
        src_frame.pack(fill=tk.X, padx=12, pady=5)

        entry_row = ttk.Frame(src_frame)
        entry_row.pack(fill=tk.X)
        iso_entry = ttk.Entry(entry_row, textvariable=self.iso_path)
        iso_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        browse_btn = ttk.Button(entry_row, text="Browse ISO...", command=self.browse_iso)
        browse_btn.pack(side=tk.LEFT)

        check_btn = ttk.Button(entry_row, text="Verify", command=self.inspect_iso)
        check_btn.pack(side=tk.LEFT, padx=(5, 0))

        # Status summary line
        self.status_lbl = ttk.Label(
            src_frame, text="Select an official Windows 11 ISO to begin.", foreground="#555555"
        )
        self.status_lbl.pack(anchor=tk.W, pady=(6, 0))

        # Edition selector
        ed_row = ttk.Frame(src_frame)
        ed_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(ed_row, text="Target Edition:").pack(side=tk.LEFT, padx=(0, 8))

        self.ed_combo = ttk.Combobox(
            ed_row, textvariable=self.edition_var, state="readonly", width=45
        )
        self.ed_combo.pack(side=tk.LEFT, padx=(0, 15))

        single_chk = ttk.Checkbutton(
            ed_row, text="Trim other editions (--single-edition)", variable=self.single_edition_var
        )
        single_chk.pack(side=tk.LEFT)

        # Account & OOBE settings
        acc_row = ttk.Frame(src_frame)
        acc_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(acc_row, text="Offline Local User:").pack(side=tk.LEFT, padx=(0, 8))
        user_entry = ttk.Entry(acc_row, textvariable=self.username_var, width=18)
        user_entry.pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(
            acc_row,
            text="(Bypasses Microsoft Account setup completely)",
            foreground="#007700",
        ).pack(side=tk.LEFT)

        # Tabbed notebook for configurations
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # Tab 1: Applications / Bloatware
        self.tab_apps = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(self.tab_apps, text="Apps & Bloatware")
        self.setup_apps_tab()

        # Tab 2: Privacy
        self.tab_privacy = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(self.tab_privacy, text="Privacy & Telemetry")
        self.setup_privacy_tab()

        # Tab 3: Firefox Integration
        self.tab_firefox = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(self.tab_firefox, text="Firefox Integration")
        self.setup_firefox_tab()

        # Tab 4: Build & Console Logs
        self.tab_build = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(self.tab_build, text="Build & Logs")
        self.setup_build_tab()

        # Tab 5: QEMU VM Testing
        self.tab_vm = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(self.tab_vm, text="VM Testing")
        self.setup_vm_tab()

    def setup_apps_tab(self):
        # Profile selector
        p_row = ttk.Frame(self.tab_apps)
        p_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(p_row, text="Profile: ", font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)

        for p_name in ["standard", "minimal"]:
            r = ttk.Radiobutton(
                p_row,
                text=p_name.capitalize(),
                value=p_name,
                variable=self.profile_var,
                command=self.apply_profile,
            )
            r.pack(side=tk.LEFT, padx=10)

        # Apps check frame
        scroll_frame = ttk.Frame(self.tab_apps)
        scroll_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(scroll_frame, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
        self.app_list_frame = ttk.Frame(canvas)

        self.app_list_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.app_list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        all_apps = packages.loadapps()
        for a in all_apps:
            pkg_id = a["id"]
            name = a["name"]
            is_safe = a.get("safe to remove", False)
            reason = a.get("reason", "")

            var = tk.BooleanVar(value=is_safe)
            self.app_checks[pkg_id] = var

            row = ttk.Frame(self.app_list_frame)
            row.pack(fill=tk.X, anchor=tk.W, pady=2)

            if is_safe:
                chk = ttk.Checkbutton(row, text=f"Remove {name}", variable=var)
                chk.pack(side=tk.LEFT)
                lbl = ttk.Label(row, text=f" — {reason}", foreground="#666666")
                lbl.pack(side=tk.LEFT)
            else:
                chk = ttk.Checkbutton(row, text=f"[Essential] {name}", variable=var, state="disabled")
                chk.pack(side=tk.LEFT)
                lbl = ttk.Label(row, text=f" — {reason}", foreground="#007700")
                lbl.pack(side=tk.LEFT)

    def apply_profile(self):
        prof = self.profile_var.get()
        res = packages.filterapps(profile=prof)
        removed_ids = {a["id"] for a in res["remove"]}
        for pkg_id, var in self.app_checks.items():
            entry = next((a for a in packages.loadapps() if a["id"] == pkg_id), None)
            if entry and entry.get("safe to remove"):
                var.set(pkg_id in removed_ids)

    def setup_privacy_tab(self):
        ttk.Label(
            self.tab_privacy,
            text="Documented Privacy Settings (Preserving Windows Update & Security):",
            font=("Helvetica", 10, "bold"),
        ).pack(anchor=tk.W, pady=(0, 8))

        rules = privacy.loadprivacy()
        for r in rules:
            name = r["name"]
            desc = r["description"]
            var = tk.BooleanVar(value=True)
            self.privacy_checks[name] = var

            box = ttk.Frame(self.tab_privacy)
            box.pack(fill=tk.X, anchor=tk.W, pady=4)
            chk = ttk.Checkbutton(box, text=name, variable=var)
            chk.pack(anchor=tk.W)
            sub = ttk.Label(box, text=f"    {desc}", foreground="#555555", wraplength=760)
            sub.pack(anchor=tk.W)

    def setup_firefox_tab(self):
        ttk.Label(
            self.tab_firefox,
            text="Firefox-First Experience:",
            font=("Helvetica", 11, "bold"),
        ).pack(anchor=tk.W, pady=(0, 10))

        ttk.Checkbutton(
            self.tab_firefox,
            text="Install Mozilla Firefox silently during Windows Setup",
            variable=self.firefox_var,
        ).pack(anchor=tk.W, pady=4)

        ttk.Label(
            self.tab_firefox,
            text="• Automatically configures Firefox enterprise policies.json (disables studies and telemetry).\n"
            "• Sets Firefox as the default browser for HTTP, HTTPS, and HTML via OEM AppAssoc.xml.\n"
            "• Automatically bundles Firefox offline installer if found in Downloads, with winget fallback.",
            foreground="#444444",
            padding="10 5",
        ).pack(anchor=tk.W)

    def setup_build_tab(self):
        ctrl = ttk.Frame(self.tab_build)
        ctrl.pack(fill=tk.X, pady=(0, 8))

        self.build_btn = ttk.Button(
            ctrl, text="Start LiteWin Build", command=self.start_build, style="Accent.TButton"
        )
        self.build_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.progress = ttk.Progressbar(ctrl, mode="indeterminate", length=300)
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        # Live log box
        log_frame = ttk.Frame(self.tab_build)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            log_frame, wrap=tk.WORD, font=("Courier", 9), bg="#1e1e1e", fg="#d4d4d4"
        )
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_vm_tab(self):
        ttk.Label(
            self.tab_vm,
            text="Test Built ISO in QEMU Virtual Machine:",
            font=("Helvetica", 11, "bold"),
        ).pack(anchor=tk.W, pady=(0, 10))

        cfg_row = ttk.Frame(self.tab_vm)
        cfg_row.pack(fill=tk.X, pady=5)

        ttk.Label(cfg_row, text="RAM:").pack(side=tk.LEFT, padx=(0, 5))
        self.vm_ram = ttk.Combobox(cfg_row, values=["2G", "4G", "8G", "16G"], width=6)
        self.vm_ram.set("4G")
        self.vm_ram.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(cfg_row, text="CPU Cores:").pack(side=tk.LEFT, padx=(0, 5))
        self.vm_cpus = ttk.Combobox(cfg_row, values=["2", "4", "6", "8"], width=4)
        self.vm_cpus.set("4")
        self.vm_cpus.pack(side=tk.LEFT, padx=(0, 15))

        test_btn = ttk.Button(self.tab_vm, text="Launch QEMU VM", command=self.launch_vm)
        test_btn.pack(anchor=tk.W, pady=10)

        has_kvm = os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)
        code, _ = qemu.findovmf()
        status_txt = f"• KVM Acceleration: {'Available (Fast)' if has_kvm else 'Disabled'}\n"
        status_txt += f"• UEFI OVMF Firmware: {'Found' if code else 'Not Found'}\n"
        ttk.Label(self.tab_vm, text=status_txt, foreground="#444444").pack(anchor=tk.W, pady=5)

    def browse_iso(self):
        path = filedialog.askopenfilename(
            title="Select Windows 11 Installation ISO",
            filetypes=[("ISO Images", "*.iso"), ("All Files", "*.*")],
        )
        if path:
            self.iso_path.set(path)
            self.inspect_iso()

    def inspect_iso(self):
        iso_p = self.iso_path.get().strip()
        if not iso_p or not os.path.isfile(iso_p):
            messagebox.showerror("Error", "Please select a valid ISO file.")
            return

        self.status_lbl.config(text="Verifying ISO and detecting Windows editions...", foreground="#0055aa")
        self.root.update_idletasks()

        try:
            info = iso.verify(iso_p)
            if not info.get("valid"):
                self.status_lbl.config(
                    text=f"Invalid ISO: {info.get('error') or info.get('missing files')}",
                    foreground="#aa0000",
                )
                return

            size_gb = round(info["size"] / (1024**3), 2)
            eds = image.editions(iso_p)
            self.detected_editions = eds

            options = [f"[{e['index']}] {e['name']} ({e['edition']}) - {e['architecture']}" for e in eds]
            self.ed_combo["values"] = options

            # default to Pro if found, otherwise first edition
            pro_idx = next(
                (i for i, e in enumerate(eds) if "pro" in e["name"].lower() or "pro" in e["edition"].lower()),
                0,
            )
            self.ed_combo.current(pro_idx)

            self.status_lbl.config(
                text=f"Verified Windows 11 ISO ({size_gb} GB, {info['image type'].upper()}). Found {len(eds)} editions.",
                foreground="#008800",
            )
        except Exception as e:
            self.status_lbl.config(text=f"Error reading ISO: {e}", foreground="#aa0000")

    def log(self, message):
        self.log_queue.put(message)

    def process_logs(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.log_text.insert(tk.END, f"{msg}\n")
            self.log_text.see(tk.END)
        self.root.after(100, self.process_logs)

    def start_build(self):
        if self.build_active:
            return

        iso_p = self.iso_path.get().strip()
        if not iso_p or not os.path.isfile(iso_p):
            messagebox.showerror("Error", "Select a valid Windows 11 ISO before building.")
            return

        ed_str = self.edition_var.get()
        ed_idx = None
        if ed_str and ed_str.startswith("["):
            try:
                ed_idx = int(ed_str.split("]")[0].lstrip("["))
            except Exception:
                pass

        self.build_active = True
        self.build_btn.config(state="disabled")
        self.progress.start(10)
        self.tabs.select(self.tab_build)

        self.log("=" * 60)
        self.log(f"[*] LiteWin Build Started at {time.strftime('%X')}")
        self.log(f"[*] Source ISO: {iso_p}")
        self.log(f"[*] Profile: {self.profile_var.get()}")
        user_name = self.username_var.get().strip() or "User"
        self.log(f"[*] Offline User: {user_name} (MSA Bypassed)")
        if ed_idx:
            self.log(f"[*] Target Edition Index: {ed_idx}")

        thread = threading.Thread(
            target=self.run_build_worker, args=(iso_p, ed_idx, user_name), daemon=True
        )
        thread.start()

    def run_build_worker(self, iso_p, ed_idx, user_name="User"):
        try:
            self.log("[*] Initializing build workspace...")
            res = builder.build(
                src_iso=iso_p,
                profile=self.profile_var.get(),
                edition_idx=ed_idx,
                single_edition=self.single_edition_var.get(),
                username=user_name,
            )
            self.log("[+] Build completed successfully!")
            self.log(f"[+] Output ISO: {res['iso path']}")
            self.log(f"[+] Size: {res['size mb']} MB")
            self.log(f"[+] SHA-256: {res['sha256']}")
            self.log(f"[+] Audit Report: {res['audit report']}")
            self.out_iso_path.set(res["iso path"])
            messagebox.showinfo("Success", f"LiteWin build complete!\n\nISO: {res['iso path']}")
        except Exception as e:
            self.log(f"[-] Build failed: {e}")
            messagebox.showerror("Build Failed", str(e))
        finally:
            self.progress.stop()
            self.build_btn.config(state="normal")
            self.build_active = False

    def launch_vm(self):
        iso_p = self.out_iso_path.get() or self.iso_path.get()
        if not iso_p or not os.path.isfile(iso_p):
            messagebox.showerror("Error", "No valid ISO available to test.")
            return

        ram = self.vm_ram.get()
        cpus = int(self.vm_cpus.get())

        try:
            res = qemu.testrun(iso_p, ram=ram, cpus=cpus, dry=False)
            messagebox.showinfo("VM Started", f"Launched QEMU Virtual Machine (PID {res['pid']}).")
        except Exception as e:
            messagebox.showerror("VM Launch Error", str(e))


def launch():
    try:
        root = tk.Tk()
        app = GuiApp(root)
        root.mainloop()
    except Exception as e:
        print(f"[*] Desktop GUI could not be initialized ({e}). Launching LiteWin Web GUI...")
        from litewin import webgui
        webgui.launch()


if __name__ == "__main__":
    launch()
