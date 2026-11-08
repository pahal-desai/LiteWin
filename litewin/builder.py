import os
import shutil

from litewin import iso
from litewin import image
from litewin import workspace
from litewin import packages
from litewin import privacy
from litewin import firefox
from litewin import compat
from litewin import manifest
from litewin import repack
from litewin import unattend


def build(src_iso, out_iso=None, profile="standard", edition_idx=None, root=None, single_edition=False):
    # validate source ISO
    iso_info = iso.verify(src_iso)
    if not iso_info.get("valid"):
        raise ValueError(f"invalid source ISO: {iso_info.get('error') or iso_info.get('missing files')}")

    # detect editions
    eds = image.editions(src_iso)
    if not eds:
        raise RuntimeError("could not detect any Windows editions in ISO")

    # pick target edition
    target_ed = None
    if edition_idx:
        for e in eds:
            if e["index"] == edition_idx:
                target_ed = e
                break
    if not target_ed:
        # prefer Pro if available, otherwise first edition
        for e in eds:
            if "pro" in e["edition"].lower() or "pro" in e["name"].lower():
                target_ed = e
                break
        if not target_ed:
            target_ed = eds[0]

    # plan customization
    pkg_plan = packages.filterapps(profile=profile)
    priv_rules = privacy.loadprivacy()

    # run compatibility audit
    audit_res = compat.audit({
        "build": target_ed.get("build"),
        "removals": pkg_plan["remove"],
    })
    if not audit_res["compatible"]:
        raise RuntimeError(f"compatibility audit failed: {audit_res['errors']}")

    # setup build workspace
    ws = workspace.setup(root=root, name="litewin_build")
    extracted = ws["extracted"]
    outdir = ws["out"]

    if not out_iso:
        safe_name = target_ed["name"].replace(" ", "_")
        out_iso = os.path.join(outdir, f"LiteWin_{safe_name}.iso")

    try:
        # extract ISO contents safely
        iso.extract(src_iso, extracted)

        # optionally export single edition to trim multi-edition bloat
        wim_path = os.path.join(extracted, "sources", "install.wim")
        if single_edition and os.path.isfile(wim_path):
            lean_wim = os.path.join(extracted, "sources", "install_lean.wim")
            image.export(wim_path, target_ed["index"], lean_wim, name=target_ed["name"])
            os.replace(lean_wim, wim_path)

        # setup OEM scripts folder for native, non-destructive deployment
        oem_scripts = os.path.join(extracted, "sources", "$OEM$", "$$", "Setup", "Scripts")
        os.makedirs(oem_scripts, exist_ok=True)

        # write privacy script
        with open(os.path.join(oem_scripts, "apply-privacy.ps1"), "w", encoding="utf-8") as f:
            f.write(privacy.makescript(priv_rules))

        # write package removal script
        with open(os.path.join(oem_scripts, "remove-packages.ps1"), "w", encoding="utf-8") as f:
            f.write(packages.makescript(pkg_plan["remove"]))

        # write firefox bundle
        firefox.bundle(oem_scripts)

        # write autounattend.xml
        unattend_content = unattend.generate(
            edition=target_ed["name"],
            lang=target_ed.get("language", "en-US"),
        )
        with open(os.path.join(extracted, "autounattend.xml"), "w", encoding="utf-8") as f:
            f.write(unattend_content)

        # generate bootable ISO using xorriso
        repack_info = repack.repack(
            sourcedir=extracted,
            outiso=out_iso,
            volid="LITEWIN",
        )

        # verify generated ISO
        gen_verify = iso.verify(out_iso)
        if not gen_verify.get("valid"):
            raise RuntimeError(f"generated ISO failed verification: {gen_verify}")

        # calculate hash of generated ISO
        gen_hash = iso.sha256(out_iso)

        # create and save manifest and markdown audit report
        manifest_data = {
            "iso": {
                "iso path": src_iso,
                "size bytes": iso_info["size"],
                "sha256": iso_info.get("sha256", "uncalculated"),
            },
            "image": target_ed,
            "profile": profile,
            "removals": pkg_plan["remove"],
            "retained": pkg_plan["retain"],
            "privacy": priv_rules,
            "firefox": {
                "enabled": True,
                "default browser": True,
                "telemetry disabled": True,
            },
            "output iso": {
                "iso path": out_iso,
                "size bytes": repack_info["size bytes"],
                "sha256": gen_hash,
            },
            "warnings": audit_res["warnings"],
            "errors": audit_res["errors"],
        }

        mf = manifest.create(manifest_data)
        saved = manifest.save(mf, os.path.dirname(os.path.abspath(out_iso)))

        return {
            "build result": "success",
            "iso path": out_iso,
            "size mb": repack_info["size mb"],
            "sha256": gen_hash,
            "manifest": saved["manifest"],
            "audit report": saved["report"],
            "edition": target_ed["name"],
            "workspace": ws["root"],
        }

    except Exception:
        # clean up on critical failure
        raise
