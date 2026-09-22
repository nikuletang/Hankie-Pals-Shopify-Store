#!/usr/bin/env python3
"""Check every section's {% schema %} against the rules Shopify enforces on
upload. Shopify only reports the first failure, and only once you paste the
file in, so checking locally is faster than finding out one error at a time.

    python3 scripts/check-schemas.py
"""
import json
import pathlib
import re
import sys

SECTIONS = pathlib.Path(__file__).resolve().parent.parent / "sections"


def check(path):
    text = path.read_text()
    match = re.search(r"\{% schema %\}(.*?)\{% endschema %\}", text, re.S)
    if not match:
        return [f"{path.name}: no schema block"]

    try:
        schema = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        return [f"{path.name}: schema is not valid JSON — {exc}"]

    problems = []
    groups = [("", schema.get("settings", []))]
    for block in schema.get("blocks", []):
        groups.append((f"blocks/{block.get('type', '?')}: ", block.get("settings", [])))

    for prefix, settings in groups:
        seen = set()
        for setting in settings:
            sid = setting.get("id")
            if sid:
                if sid in seen:
                    problems.append(f"{path.name}: {prefix}duplicate setting id '{sid}'")
                seen.add(sid)

            if setting.get("type") == "range":
                lo, hi, step = setting["min"], setting["max"], setting["step"]
                steps = (hi - lo) / step + 1
                if steps > 101:
                    problems.append(
                        f"{path.name}: {prefix}range '{sid}' has {steps:.0f} steps "
                        f"({lo}-{hi} by {step}); Shopify allows at most 101"
                    )
                if (hi - lo) % step != 0:
                    problems.append(
                        f"{path.name}: {prefix}range '{sid}' — {hi} is not reachable "
                        f"from {lo} in steps of {step}"
                    )
                unit = setting.get("unit")
                if unit is not None and len(str(unit)) > 3:
                    problems.append(
                        f"{path.name}: {prefix}range '{sid}' unit {unit!r} is "
                        f"{len(str(unit))} characters; Shopify allows at most 3"
                    )
                default = setting.get("default")
                if default is not None and not (lo <= default <= hi):
                    problems.append(
                        f"{path.name}: {prefix}range '{sid}' default {default} "
                        f"is outside {lo}-{hi}"
                    )
                # Being inside the range is not enough: Shopify only accepts a
                # default the slider can actually land on. min 500 step 10 puts
                # 749 between two stops, and the theme editor refuses the file
                # on paste with "default must be a step in the range" -- which
                # is the whole section rejected, not the one setting.
                elif default is not None and (default - lo) % step != 0:
                    near = lo + round((default - lo) / step) * step
                    problems.append(
                        f"{path.name}: {prefix}range '{sid}' default {default} "
                        f"is not a stop on {lo}-{hi} by {step}; nearest is {near}"
                    )

            if setting.get("type") == "select":
                values = [o["value"] for o in setting.get("options", [])]
                default = setting.get("default")
                if default is not None and default not in values:
                    problems.append(
                        f"{path.name}: {prefix}select '{sid}' default '{default}' "
                        f"is not one of its options"
                    )

    # a setting read in the body but never declared renders as nothing
    body = text[: text.index("{% schema %}")]
    declared = {s["id"] for s in schema.get("settings", []) if s.get("id")}
    for used in sorted(set(re.findall(r"\bs\.([a-z_]+)", body))):
        if used not in declared:
            problems.append(f"{path.name}: body reads s.{used}, which no setting declares")

    # A setting interpolated into CSS without a fallback breaks on any section
    # instance that predates it — see the README. Only CSS: a nil there leaves
    # `--x: ;`, which voids the declaration and sometimes the rule around it.
    # In text a nil renders as nothing, which is what an optional setting is
    # supposed to do, and demanding `| default: ''` for that trains you to
    # ignore the warning.
    css = ''.join(re.findall(r"\{%\s*style\s*%\}(.*?)\{%\s*endstyle\s*%\}", body, re.S))
    css += ''.join(re.findall(r'style="(.*?)"', body, re.S))
    for bare in sorted(set(re.findall(r"\{\{ s\.([a-z_]+)\s*\}\}", css))):
        problems.append(f"{path.name}: {{{{ s.{bare} }}}} has no `| default:` fallback")

    return problems


def main():
    problems = []
    files = sorted(SECTIONS.glob("*.liquid"))
    for path in files:
        problems.extend(check(path))

    for problem in problems:
        print(problem)

    print(f"\n{len(files)} section(s) checked, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
