import argparse
import json
import os
import sys

from litewin import iso
from litewin import image
from litewin import workspace
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

    args = parser.parse_args()

    if not args.cmd:
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


if __name__ == "__main__":
    run()
