import argparse
import json
import os
import sys

from litewin import iso
from litewin import image
from litewin import workspace
from litewin import packages
from litewin import privacy
from litewin import builder
from litewin import qemu
from litewin import bench
from litewin import gui
from litewin import version


def show(data):
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list):
                print(f"{k}:")
                for item in v:
                    print(f"  - {item}")
            else:
                print(f"{k}: {v}")
    else:
        print(data)


def run():
    parser = argparse.ArgumentParser(
        prog="litewin",
        description="LiteWin - Windows, without the baggage.",
    )
    parser.add_argument("--version", action="version", version=f"litewin {version}")
    subs = parser.add_subparsers(dest="cmd", help="command to run")

    # gui command
    subs.add_parser("gui", help="launch LiteWin graphical user interface")

    # check command
    chk = subs.add_parser("check", help="check ISO structure and required files")
    chk.add_argument("iso", help="path to Windows 11 ISO")
    chk.add_argument("--json", action="store_true", help="output json format")

    # inspect command
    insp = subs.add_parser("inspect", help="inspect ISO and calculate SHA-256")
    insp.add_argument("iso", help="path to Windows 11 ISO")
    insp.add_argument("--hash", action="store_true", help="calculate SHA-256 hash")
    insp.add_argument("--json", action="store_true", help="output json format")

    # editions command
    eds = subs.add_parser("editions", help="list available Windows editions in image")
    eds.add_argument("target", help="path to ISO or WIM file")
    eds.add_argument("--boot", action="store_true", help="list bootloader PE editions instead")
    eds.add_argument("--json", action="store_true", help="output json format")

    # extract command
    ext = subs.add_parser("extract", help="safely extract ISO contents into destination")
    ext.add_argument("iso", help="path to Windows 11 ISO")
    ext.add_argument("dest", help="destination directory")
    ext.add_argument("--pick", nargs="*", help="specific files to extract")

    # workspace command
    ws = subs.add_parser("workspace", help="manage build workspaces")
    ws.add_argument("action", choices=["new", "status", "clean"], help="workspace action")
    ws.add_argument("--path", help="workspace folder path")

    # plan command
    pln = subs.add_parser("plan", help="preview customization plan")
    pln.add_argument("--profile", default="standard", choices=["minimal", "standard"], help="customization profile")
    pln.add_argument("--json", action="store_true", help="output json format")

    # build command
    bld = subs.add_parser("build", help="build customized Windows 11 ISO")
    bld.add_argument("iso", help="source Windows 11 ISO path")
    bld.add_argument("--out", help="output customized ISO path")
    bld.add_argument("--profile", default="standard", choices=["minimal", "standard"], help="profile")
    bld.add_argument("--edition", type=int, help="edition index (e.g. 6 for Pro)")
    bld.add_argument("--single-edition", action="store_true", help="export only selected edition to trim multi-edition image size")
    bld.add_argument("--workdir", help="custom workspace root folder")

    # test command
    tst = subs.add_parser("test", help="launch or inspect QEMU test VM")
    tst.add_argument("iso", help="path to ISO to boot")
    tst.add_argument("--ram", default="4G", help="memory size (e.g. 4G)")
    tst.add_argument("--cpus", default=4, type=int, help="CPU core count")
    tst.add_argument("--dry", action="store_true", default=True, help="print command instead of launching interactive window")
    tst.add_argument("--run", action="store_true", help="actually launch QEMU window")

    # bench command
    bnc = subs.add_parser("bench", help="performance benchmark tools")
    bnc.add_argument("action", choices=["collector", "compare"], help="benchmark action")
    bnc.add_argument("--stock", help="JSON file of stock Windows metrics")
    bnc.add_argument("--litewin", help="JSON file of LiteWin metrics")

    args = parser.parse_args()

    if not args.cmd or args.cmd == "gui":
        # if a graphical display exists (or on Windows), launch GUI
        has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY") or sys.platform == "win32")
        if has_display:
            gui.launch()
            sys.exit(0)
        else:
            parser.print_help()
            sys.exit(0)

    if args.cmd == "check":
        res = iso.verify(args.iso)
        if getattr(args, "json", False):
            print(json.dumps(res, indent=2))
        else:
            show(res)
        sys.exit(0 if res.get("valid") else 1)

    if args.cmd == "inspect":
        res = iso.inspect(args.iso, checkhash=args.hash)
        if getattr(args, "json", False):
            print(json.dumps(res, indent=2))
        else:
            show(res)
        sys.exit(0 if res.get("valid") else 1)

    if args.cmd == "editions":
        role = "boot" if getattr(args, "boot", False) else "install"
        items = image.editions(args.target, role=role)
        if getattr(args, "json", False):
            print(json.dumps(items, indent=2))
        else:
            for it in items:
                print(f"[{it['index']}] {it['name']} ({it['edition']}) - build {it['build']} [{it['architecture']}]")
        sys.exit(0)

    if args.cmd == "extract":
        dest = iso.extract(args.iso, args.dest, picks=args.pick)
        print(f"extracted successfully to {dest}")
        sys.exit(0)

    if args.cmd == "workspace":
        if args.action == "new":
            dirs = workspace.setup(name="run")
            print(f"created workspace at: {dirs['root']}")
        elif args.action == "clean":
            if not args.path:
                print("specify --path to clean")
                sys.exit(1)
            workspace.clean(args.path)
            print(f"cleaned workspace: {args.path}")
        elif args.action == "status":
            if not args.path:
                print("specify --path to inspect")
                sys.exit(1)
            st = workspace.status(args.path)
            show(st)
        sys.exit(0)

    if args.cmd == "plan":
        apps = packages.filterapps(profile=args.profile)
        rules = privacy.loadprivacy()
        plan_data = {
            "profile": args.profile,
            "removals count": len(apps["remove"]),
            "retained count": len(apps["retain"]),
            "privacy settings count": len(rules),
            "removals": [a["name"] for a in apps["remove"]],
            "retained essential": [a["name"] for a in apps["retain"]],
            "privacy tweaks": [r["name"] for r in rules],
        }
        if getattr(args, "json", False):
            print(json.dumps(plan_data, indent=2))
        else:
            show(plan_data)
        sys.exit(0)

    if args.cmd == "build":
        print(f"[*] Starting LiteWin build from: {args.iso}")
        res = builder.build(
            src_iso=args.iso,
            out_iso=args.out,
            profile=args.profile,
            edition_idx=args.edition,
            root=args.workdir,
            single_edition=getattr(args, "single_edition", False),
        )
        print("[+] Build completed successfully!")
        show(res)
        sys.exit(0)

    if args.cmd == "test":
        dry = not getattr(args, "run", False)
        res = qemu.testrun(args.iso, ram=args.ram, cpus=args.cpus, dry=dry)
        show(res)
        sys.exit(0)

    if args.cmd == "bench":
        if args.action == "collector":
            print(bench.getcollector())
        elif args.action == "compare":
            if not args.stock or not args.litewin:
                print("specify both --stock and --litewin JSON files to compare")
                sys.exit(1)
            with open(args.stock, "r") as f:
                stock_data = json.load(f)
            with open(args.litewin, "r") as f:
                lite_data = json.load(f)
            cmp_res = bench.compare(stock_data, lite_data)
            print(bench.markdown(cmp_res))
        sys.exit(0)


if __name__ == "__main__":
    run()
