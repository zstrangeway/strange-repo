"""Fail on any key in values.yaml that the chart doesn't define.

Helm ignores unknown keys, so a typo - or a key a chart upgrade renamed -
does nothing and says nothing. A key is accepted when the nearest ancestor
the chart does define is free-form (an empty map or null), like `resources`.

Sub-charts' defaults are merged in under their names, the way Helm sees
them: the parent chart's own values for a sub-chart win over the sub-chart's.

Some values are handed to Kubernetes as a whole object (a pod's securityContext,
say) whose chart default only lists a few fields. Name those with --free-form
<dotted.path>, and anything below them is accepted.

Usage: check_helm_values.py <label> <unpacked chart dir> <our values as JSON> [--free-form path ...]
"""
import json
import pathlib
import subprocess
import sys


def load_yaml(path):
    out = subprocess.run(["yq", "-o=json", ".", str(path)], check=True, capture_output=True, text=True).stdout
    return json.loads(out or "null") or {}


def merge(base, over):
    if not (isinstance(base, dict) and isinstance(over, dict)):
        return over
    merged = dict(base)
    for key, value in over.items():
        merged[key] = merge(base.get(key), value) if key in base else value
    return merged


def leaves(node, path=()):
    if isinstance(node, dict) and node:
        for key, value in node.items():
            yield from leaves(value, path + (key,))
    else:
        yield path


def unknown(defaults, path, free_form=()):
    if any(path[: len(f)] == f for f in free_form):
        return None
    node = defaults
    for depth, key in enumerate(path):
        if not isinstance(node, dict) or not node:
            return None  # free-form from here down
        if key not in node:
            return ".".join(path[: depth + 1])
        node = node[key]
    return None


label = sys.argv[1]
chart = pathlib.Path(sys.argv[2])
defaults = load_yaml(chart / "values.yaml")
for sub in sorted((chart / "charts").glob("*/values.yaml")):
    name = sub.parent.name
    defaults[name] = merge(load_yaml(sub), defaults.get(name) or {})
ours = json.load(open(sys.argv[3]))
extra = sys.argv[4:]
free_form = [tuple(extra[i + 1].split(".")) for i, a in enumerate(extra) if a == "--free-form" and i + 1 < len(extra)]
paths = list(leaves(ours))
bad = sorted({u for p in paths if (u := unknown(defaults, p, free_form))})
if bad:
    print(f"{label}: values.yaml keys the chart doesn't have: " + ", ".join(bad))
    sys.exit(1)
print(f"{label}: all {len(paths)} values.yaml settings are keys the chart defines")
