import os
import shutil
import tempfile
import time


def setup(root=None, name="build"):
    # isolated scratch directory so we never touch original files
    stamp = time.strftime("%Y%m%d_%H%M%S")
    folder = f"{name}_{stamp}"
    base = root if root else os.path.join(os.getcwd(), "workspaces")
    workdir = os.path.abspath(os.path.join(base, folder))

    dirs = {
        "root": workdir,
        "extracted": os.path.join(workdir, "extracted"),
        "staging": os.path.join(workdir, "staging"),
        "unattend": os.path.join(workdir, "unattend"),
        "out": os.path.join(workdir, "out"),
    }

    for path in dirs.values():
        os.makedirs(path, exist_ok=True)

    return dirs


def clean(path):
    if not path or not os.path.exists(path):
        return False
    shutil.rmtree(path, ignore_errors=True)
    return True


def status(path):
    if not path or not os.path.exists(path):
        return {"exists": False}
    
    total = 0
    count = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if not os.path.islink(fp):
                total += os.path.getsize(fp)
                count += 1

    return {
        "exists": True,
        "path": path,
        "files": count,
        "bytes": total,
        "mb": round(total / (1024 * 1024), 2),
    }
