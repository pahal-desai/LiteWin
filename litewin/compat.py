import json
import os

DATADIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def loadcompat():
    path = os.path.join(DATADIR, "compatibility.json")
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get(name):
    for item in loadcompat():
        if item.get("component name", "").lower() == name.lower():
            return item
    return None


def audit(plan):
    # cross-references proposed plan against the compatibility database
    removals = plan.get("removals", [])
    build = str(plan.get("build", ""))
    compat_db = {c["component name"].lower(): c for c in loadcompat()}

    warnings = []
    errors = []

    for item in removals:
        name = item.get("id") or item.get("component name") or str(item)
        entry = compat_db.get(name.lower())

        if not entry:
            warnings.append(f"component '{name}' has unknown compatibility status")
            continue

        support = entry.get("removal support")
        if support == "unsupported":
            errors.append(
                f"component '{name}' cannot be removed: {entry.get('known issues')}"
            )
        elif support == "not recommended":
            warnings.append(
                f"removing '{name}' is not recommended: {entry.get('known issues')}"
            )

        # check build compatibility
        supported_builds = entry.get("windows build compatibility", [])
        if build and supported_builds:
            prefix = build.split(".")[0]
            if prefix not in supported_builds:
                warnings.append(
                    f"component '{name}' compatibility on build {build} is unverified"
                )

        # check dependencies
        deps = entry.get("dependencies", [])
        for d in deps:
            for other in removals:
                other_name = other.get("id") or other.get("component name") or str(other)
                if other_name.lower() == d.lower():
                    errors.append(
                        f"conflict: '{name}' requires '{d}', but '{d}' is also marked for removal"
                    )

    return {
        "compatible": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "checked": len(removals),
    }
