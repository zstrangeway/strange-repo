"""Fail on any key in values.yaml that the chart doesn't define.

Helm ignores unknown keys, so a typo - or a key a chart upgrade renamed -
does nothing and says nothing. A key is accepted when the nearest ancestor
the chart does define is free-form (an empty map or null), like `resources`.

Sub-charts' defaults are merged in under their names, the way Helm sees
them: the parent chart's own values for a sub-chart win over the sub-chart's.

Usage: check_values.py <unpacked chart dir> <our values as JSON>
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


def unknown(defaults, path):
    node = defaults
    for depth, key in enumerate(path):
        if not isinstance(node, dict) or not node:
            return None  # free-form from here down
        if key not in node:
            return ".".join(path[: depth + 1])
        node = node[key]
    return None


chart = pathlib.Path(sys.argv[1])
defaults = load_yaml(chart / "values.yaml")
for sub in sorted((chart / "charts").glob("*/values.yaml")):
    name = sub.parent.name
    defaults[name] = merge(load_yaml(sub), defaults.get(name) or {})
ours = json.load(open(sys.argv[2]))
paths = list(leaves(ours))
bad = sorted({u for p in paths if (u := unknown(defaults, p))})
if bad:
    print("monitoring: values.yaml keys the chart doesn't have: " + ", ".join(bad))
    sys.exit(1)
print(f"monitoring: all {len(paths)} values.yaml settings are keys the chart defines")
