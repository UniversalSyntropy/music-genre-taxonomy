#!/usr/bin/env python3
"""Turn a GitHub issue-form body into an entry in contrib/hand-links.yaml.

    python tools/suggest.py --issue N [--body-file PATH] [--comment-out PATH] [--check-only]

The body comes from --body-file, else from the env var ISSUE_BODY (never from argv).
Exit 0 = valid, 1 = invalid, 2 = internal error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
KEY_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
URL_RE = re.compile(r"^https://[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/[A-Za-z0-9._~%!$&'()*+,;=:@/?#-]*)?$")
HEADER = (
    "# Contributed links. One entry per accepted suggestion. tools/suggest.py writes this file; do not edit by hand.\n"
    "# Each entry: child and parent are node keys; the names are the node names at the time of the suggestion.\n"
)
ENTRY_KEYS = ("child", "child_name", "parent", "parent_name", "source_url", "issue")
ADD, REMOVE = "Add a parent", "Remove a parent"
NO_RESPONSE = "_No response_"
LICENCE_RE = re.compile(r"^- \[[xX]\] I agree that this suggestion is published under CC BY 4\.0\.$")


def parse_issue(body: str) -> dict:
    """Map labels to values. Keys: change, child, parent, url, note (missing -> absent)."""
    text = (body or "").replace("\r\n", "\n").replace("\r", "\n")
    sections: dict[str, str] = {}
    label = None
    buf: list[str] = []
    for line in text.split("\n"):
        m = re.match(r"^###[ \t]+(.*?)[ \t]*$", line)
        if m:
            if label is not None:
                sections[label] = "\n".join(buf).strip()
            label, buf = m.group(1).strip(), []
        elif label is not None:
            buf.append(line)
    if label is not None:
        sections[label] = "\n".join(buf).strip()
    out = {}
    for lab, k in (("Change", "change"), ("Genre key", "child"), ("Parent key", "parent"),
                   ("Public source URL", "url"), ("Note", "note")):
        if lab in sections:
            v = sections[lab].strip()
            out[k] = "" if v == NO_RESPONSE else v
    out["licence"] = any(LICENCE_RE.match(l.strip()) for l in sections.get("Licence", "").split("\n"))
    return out


def safe(s, n=80) -> str:
    return re.sub(r"[^a-z0-9-]", "", str(s).lower())[:n]


def _pairs(entries):
    return {(e["child"], e["parent"]) for e in entries}


def _reaches(edges, start, goal) -> bool:
    up: dict[str, list[str]] = {}
    for c, p in edges:
        up.setdefault(c, []).append(p)
    seen, stack = set(), [start]
    while stack:
        n = stack.pop()
        if n == goal:
            return True
        if n in seen:
            continue
        seen.add(n)
        stack.extend(up.get(n, ()))
    return False


def graph_edges(doc, contrib) -> set:
    e = {(l["child"], l["parent"]) for l in doc["links"]}
    e |= _pairs(contrib["add_edges"])
    e -= _pairs(contrib["remove_edges"])
    return e


def validate(sug: dict, doc: dict, contrib: dict) -> list[str]:
    errs: list[str] = []
    change = sug.get("change")
    if change not in (ADD, REMOVE):
        errs.append("The Change field must be 'Add a parent' or 'Remove a parent'.")
    if not sug.get("licence"):
        errs.append("The Licence box must be ticked: the suggestion is published under CC BY 4.0.")
    nodes = {n["key"] for n in doc["nodes"]}
    ok = {}
    for field, label in (("child", "Genre key"), ("parent", "Parent key")):
        v = sug.get(field)
        if not v:
            errs.append(f"The {label} field is missing.")
        elif len(v) > 80 or not KEY_RE.match(v):
            errs.append(f"The {label} field is not a valid key (lowercase letters, digits and single hyphens, 80 characters at most).")
        elif v not in nodes:
            errs.append(f"The key '{safe(v)}' in the {label} field is not a genre in the data.")
        else:
            ok[field] = v
    url = sug.get("url")
    if not url:
        errs.append("The Public source URL field is missing.")
    elif len(url) > 300 or not URL_RE.fullmatch(url):
        errs.append("The Public source URL must be a plain https link of 300 characters or fewer, with no spaces, quotes, backticks, angle brackets or backslashes.")
    if "child" in ok and "parent" in ok:
        c, p = ok["child"], ok["parent"]
        pair = (c, p)
        doc_pairs = {(l["child"], l["parent"]) for l in doc["links"]}
        if c == p:
            errs.append("The genre and the parent are the same key.")
        elif change == ADD:
            if pair in doc_pairs:
                errs.append(f"The link {c} -> {p} is already in the data.")
            elif pair in _pairs(contrib["add_edges"]):
                errs.append(f"The link {c} -> {p} is already suggested.")
            elif _reaches(graph_edges(doc, contrib), p, c):
                errs.append(f"The link {c} -> {p} would make a cycle: '{c}' is already above '{p}'.")
        elif change == REMOVE:
            if pair not in doc_pairs:
                errs.append(f"The link {c} -> {p} is not in the data, so it cannot be removed.")
            elif pair in _pairs(contrib["remove_edges"]):
                errs.append(f"The removal of {c} -> {p} is already suggested.")
    return errs


def empty_contrib() -> dict:
    return {"version": 1, "add_edges": [], "remove_edges": []}


def drop_issue(contrib: dict, issue: int) -> dict:
    return {"version": 1,
            "add_edges": [e for e in contrib["add_edges"] if e.get("issue") != issue],
            "remove_edges": [e for e in contrib["remove_edges"] if e.get("issue") != issue]}


def apply(sug: dict, doc: dict, contrib: dict, issue: int) -> dict:
    names = {n["key"]: n["name"] for n in doc["nodes"]}
    entry = {"child": sug["child"], "child_name": names[sug["child"]], "parent": sug["parent"],
             "parent_name": names[sug["parent"]], "source_url": sug["url"], "issue": issue}
    lst = "add_edges" if sug["change"] == ADD else "remove_edges"
    new = {"version": 1, "add_edges": list(contrib["add_edges"]), "remove_edges": list(contrib["remove_edges"])}
    new[lst].append(entry)
    for k in ("add_edges", "remove_edges"):
        new[k].sort(key=lambda e: (e["child"], e["parent"]))
    return new


def _scalar(v) -> str:
    if isinstance(v, int):
        return str(v)
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .&+-]*", v) and not v.endswith(" ") and yaml.safe_load(v) == v:
        return v
    return json.dumps(v, ensure_ascii=False)


def dump_contrib(contrib: dict) -> str:
    out = [HEADER + "version: 1\n"]
    for k in ("add_edges", "remove_edges"):
        if not contrib[k]:
            out.append(f"{k}: []\n")
            continue
        out.append(f"{k}:\n")
        for e in contrib[k]:
            parts = []
            for f in ENTRY_KEYS:
                v = json.dumps(e[f]) if f == "source_url" else _scalar(e[f])
                parts.append(f"{f}: {v}")
            out.append("  - {" + ", ".join(parts) + "}\n")
    text = "".join(out)
    back = yaml.safe_load(text)
    want = {"version": 1, "add_edges": contrib["add_edges"], "remove_edges": contrib["remove_edges"]}
    if back != want:
        raise ValueError("contrib file does not round-trip through YAML")
    return text


def load_contrib(p: Path) -> dict:
    if not p.exists():
        return empty_contrib()
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(d, dict) or d.get("version") != 1:
        raise ValueError("contrib file has a wrong version")
    return {"version": 1, "add_edges": d.get("add_edges") or [], "remove_edges": d.get("remove_edges") or []}


def comment_ok(sug, issue) -> str:
    verb = "add the parent link" if sug["change"] == ADD else "remove the parent link"
    return (f"The suggestion passed the automatic checks.\n\n"
            f"- **Action:** {verb}\n- **Link:** `{sug['child']}` -> `{sug['parent']}`\n\n"
            f"A maintainer will review it. If you edit the issue, the checks run again.\n")


def comment_bad(errs) -> str:
    return ("The suggestion did not pass the automatic checks.\n\n" + "\n".join(f"- {e}" for e in errs) +
            "\n\nEdit the issue to fix these points. The checks run again after each edit.\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--issue", type=int, required=True)
    ap.add_argument("--body-file")
    ap.add_argument("--data", default=str(ROOT / "data" / "taxonomy.json"))
    ap.add_argument("--contrib", default=str(ROOT / "contrib" / "hand-links.yaml"))
    ap.add_argument("--comment-out")
    ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args(argv)
    try:
        body = Path(a.body_file).read_text(encoding="utf-8") if a.body_file else os.environ.get("ISSUE_BODY", "")
        doc = json.loads(Path(a.data).read_text(encoding="utf-8"))
        cp = Path(a.contrib)
        contrib = drop_issue(load_contrib(cp), a.issue)
        sug = parse_issue(body)
        errs = validate(sug, doc, contrib)
        if errs:
            text, rc = comment_bad(errs), 1
        else:
            new = apply(sug, doc, contrib, a.issue)
            if not a.check_only:
                cp.write_text(dump_contrib(new), encoding="utf-8")
            text, rc = comment_ok(sug, a.issue), 0
        if a.comment_out:
            Path(a.comment_out).write_text(text, encoding="utf-8")
        print(text)
        return rc
    except Exception as e:  # internal error: never echo user text
        print(f"Internal error: {type(e).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
