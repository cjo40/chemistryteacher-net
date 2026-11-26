#!/usr/bin/env python3
"""Rebuild the activity list in README.md from site.json.

Run after adding or changing an activity:   python3 make_readme.py
Only the part between the ACTIVITIES markers is replaced; everything else in
README.md is left alone. Uses only the Python standard library.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
START = "<!-- ACTIVITIES:START (made by make_readme.py from site.json; edit site.json, not this list) -->"
END = "<!-- ACTIVITIES:END -->"


def cell(text):
    return " ".join(str(text).split()).replace("|", "\\|")


def build_section(site):
    base = site.get("base_url", "https://chemistryteacher.net").rstrip("/")
    host = base.split("://", 1)[-1]
    units = site.get("units", [])
    acts = []
    for slug in sorted(p.stem for p in (ROOT / "activities").glob("*.html")):
        meta = dict(site.get("activities", {}).get(slug, {}))
        meta.setdefault("name", slug.replace("-", " ").title())
        meta.setdefault("unit", "More Activities")
        meta.setdefault("order", 99)
        meta["slug"] = slug
        acts.append(meta)
    acts.sort(key=lambda a: (units.index(a["unit"]) if a["unit"] in units else len(units), a["order"], a["name"]))

    lines = [START, "", f"## All activities ({len(acts)})", "",
             f"Every activity is free, runs in any browser (Chromebooks, Windows, iPads, phones) and needs no login. "
             f"Open them at [{host}]({base}).", ""]
    for unit in units + ["More Activities"]:
        group = [a for a in acts if a["unit"] == unit]
        if not group:
            continue
        lines += [f"### {unit}", "", "| Activity | What students do | Topics |", "|---|---|---|"]
        for a in group:
            url = f"{base}/{a['slug']}"
            what = a.get("card") or a.get("description", "")
            topics = ", ".join(a.get("topics", [])[:8])
            ws = a.get("worksheets") or []
            if ws:
                what += " Printable worksheet: " + ", ".join(
                    f"[{w['file'].rsplit('.', 1)[-1].upper()}]({base}/assets/worksheets/{w['file']})" for w in ws if w.get("file"))
            lines.append(f"| **[{cell(a['name'])}]({url})** | {cell(what)} | {cell(topics)} |")
        lines.append("")
    lines.append(END)
    return "\n".join(lines)


def main():
    site = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    section = build_section(site)
    if START in readme and END in readme:
        before = readme.split(START, 1)[0]
        after = readme.split(END, 1)[1]
        readme = before + section + after
    else:
        # first run: put the list right after the opening paragraph
        head, sep, rest = readme.partition("\n\n")
        head2, sep2, rest2 = rest.partition("\n\n")
        readme = head + sep + head2 + "\n\n" + section + "\n\n" + rest2
    readme_path.write_text(readme, encoding="utf-8")
    print("README.md updated:", section.count("| **["), "activities")


if __name__ == "__main__":
    main()
