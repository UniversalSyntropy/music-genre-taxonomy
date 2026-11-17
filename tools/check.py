#!/usr/bin/env python3
"""Check the data, the docs and the repo. Needs: jsonschema.

Usage: python tools/check.py [--data FILE] [--fix-counts]
Checks: schema, integrity, CSV row counts, privacy scan, doc counts, Markdown links.
Exit code 0 means all passed.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors: list[str] = []


def fail(msg: str):
    errors.append(msg)


def git_files(root: Path):
    try:
        a = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True).stdout.split("\n")
        b = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=root, capture_output=True,
                           text=True, check=True).stdout.split("\n")
    except Exception as e:
        fail(f"Cannot list files with git: {e}")
        return []
    seen = sorted({x for x in a + b if x})
    return [root / x for x in seen if (root / x).is_file()]


def check_schema(doc):
    import jsonschema
    schema = json.loads((ROOT / "schema" / "taxonomy.schema.json").read_text(encoding="utf-8"))
    v = jsonschema.Draft202012Validator(schema)
    errs = sorted(v.iter_errors(doc), key=lambda e: list(e.absolute_path))
    for e in errs[:10]:
        fail(f"Schema: {'/'.join(str(p) for p in e.absolute_path) or '(top)'}: {e.message[:200]}")
    if len(errs) > 10:
        fail(f"Schema: {len(errs) - 10} more errors not shown")
    return not errs


def stats(doc):
    nodes, links = doc["nodes"], doc["links"]
    parents, children = defaultdict(set), defaultdict(set)
    nlinks = defaultdict(int)
    for l in links:
        nlinks[l["child"]] += 1
        parents[l["child"]].add(l["parent"])
        children[l["parent"]].add(l["child"])
    keys = [n["key"] for n in nodes]
    ext = lambda n, k: k in n["external"]
    return {
        "nodes": len(nodes), "links": len(links), "aliases": len(doc["aliases"]),
        "tag_level": sum(n["tag_level"] for n in nodes),
        "roots": sum(1 for k in keys if not parents[k]),
        "isolated": sum(1 for k in keys if not parents[k] and not children[k]),
        "multi_parent": sum(1 for k in keys if len(parents[k]) >= 2),  # two or more different parents
        "multi_link": sum(1 for k in keys if nlinks[k] >= 2),  # two or more link rows, even with one parent
        "nodes_musicbrainz": sum(1 for n in nodes if n["source"] == "musicbrainz"),
        "nodes_discogs": sum(1 for n in nodes if n["source"] == "discogs"),
        "links_wikidata": sum(1 for l in links if l["source"] == "wikidata"),
        "links_discogs": sum(1 for l in links if l["source"] == "discogs"),
        "links_musicbrainz": sum(1 for l in links if l["source"] == "musicbrainz"),
        "links_hand": sum(1 for l in links if l["source"] == "hand"),
        "aliases_hand": sum(1 for a in doc["aliases"] if a["source"] == "hand"),
        "links_high": sum(1 for l in links if l.get("confidence") == "high"),
        "links_medium": sum(1 for l in links if l.get("confidence") == "medium"),
        "links_low": sum(1 for l in links if l.get("confidence") == "low"),
        "proposals": len(doc.get("proposals", [])),
        "with_musicbrainz_id": sum(1 for n in nodes if ext(n, "musicbrainz_id")),
        "with_wikidata_id": sum(1 for n in nodes if ext(n, "wikidata_id")),
        "with_discogs_name": sum(1 for n in nodes if ext(n, "discogs_name")),
    }


def check_integrity(doc, data_path: Path):
    nodes, links, aliases = doc["nodes"], doc["links"], doc["aliases"]
    keys = [n["key"] for n in nodes]
    kset = set(keys)
    if len(kset) != len(keys):
        fail("Integrity: node keys are not unique.")
    for k in keys:
        if not all(p and p.isalnum() and p == p.lower() for p in k.split("-")):
            fail(f"Integrity: key '{k}' has a character that is not a lowercase letter or digit.")
    codes = {s["code"] for s in doc["sources"]}
    seen_links = set()
    adj = defaultdict(list)
    for l in links:
        for f in ("child", "parent"):
            if l[f] not in kset:
                fail(f"Integrity: link {f} '{l[f]}' is not a node.")
        if l["child"] == l["parent"]:
            fail(f"Integrity: link {l['child']} points to itself.")
        t = (l["child"], l["parent"], l["source"])
        if t in seen_links:
            fail(f"Integrity: duplicate link {t}.")
        seen_links.add(t)
        adj[l["child"]].append(l["parent"])
        if l["source"] not in codes:
            fail(f"Integrity: link source '{l['source']}' is not in sources.")
    # cycle check (iterative DFS)
    state = {}
    for s in keys:
        if s in state:
            continue
        stack = [(s, iter(adj[s]))]
        state[s] = 1
        while stack:
            n, it = stack[-1]
            for m in it:
                if state.get(m) == 1:
                    fail(f"Integrity: cycle through '{m}'.")
                elif m not in state:
                    state[m] = 1
                    stack.append((m, iter(adj[m])))
                    break
            else:
                state[n] = 2
                stack.pop()
    for a in aliases:
        if a["node"] not in kset:
            fail(f"Integrity: alias '{a['name']}' points to missing node '{a['node']}'.")
        if a["source"] == "filetag":
            fail(f"Integrity: alias '{a['name']}' has source filetag. This is private data.")
        if a["source"] not in codes:
            fail(f"Integrity: alias source '{a['source']}' is not in sources.")
    for n in nodes:
        for s in [n["source"], *n["seen_in"]]:
            if s not in codes:
                fail(f"Integrity: node '{n['key']}' uses source '{s}' that is not in sources.")
    for c in codes:
        if c == "filetag":
            fail("Integrity: sources lists filetag.")
    st = stats(doc)
    for k in ("nodes", "links", "aliases", "tag_level"):
        if doc["counts"][k] != st[k]:
            fail(f"Integrity: counts.{k} is {doc['counts'][k]} but the data has {st[k]}.")
    # confidence follows from source and basis (tools/build.py CONFIDENCE)
    rule = {("wikidata", "sourced"): "high", ("musicbrainz", "sourced"): "high", ("hand", "sourced"): "high",
            ("wikidata", "derived"): "medium", ("discogs", "derived"): "low"}
    for l in links:
        if rule.get((l["source"], l["basis"])) != l.get("confidence"):
            fail(f"Integrity: link {l['child']} -> {l['parent']} ({l['source']}, {l['basis']}) has confidence {l.get('confidence')!r}.")
    # proposals: review list, never links
    known = set(keys)
    for r in doc.get("proposals", []):
        if r["child"] not in known or r["parent"] not in known:
            fail(f"Proposals: {r['child']} -> {r['parent']} names a key that is not a node.")
    # CSV
    d = data_path.parent
    for name, n in (("nodes.csv", len(nodes)), ("links.csv", len(links)), ("aliases.csv", len(aliases))):
        p = d / name
        if not p.exists():
            fail(f"CSV: {name} is missing next to the data file.")
            continue
        with open(p, encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
        if len(rows) - 1 != n:
            fail(f"CSV: {name} has {len(rows) - 1} rows but the JSON has {n}.")
        if name == "aliases.csv":
            si = rows[0].index("source")
            if any(r[si] == "filetag" for r in rows[1:]):
                fail("CSV: aliases.csv holds a filetag alias.")
    return st


PRIVACY = [
    ("a home path", re.compile("/Us" + "ers/|/ho" + "me/")),
    ("an e-mail address", re.compile(r"[A-Za-z0-9._%+-]+@(?!example\.com\b)[A-Za-z0-9-]+\.[A-Za-z]{2,}")),
    ("a LAN address", re.compile(r"192\.168\.")),
    ("a .local host name", re.compile(r"\b[\w-]+\.lo" + r"cal\b")),
]


def is_text(p: Path):
    try:
        b = p.read_bytes()
    except OSError:
        return None
    if b"\0" in b[:8192]:
        return None
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return None


def check_privacy(files, root: Path):
    wf = root / "local" / "privacy-words.txt"
    words = []
    if wf.exists():
        words = [w.strip() for w in wf.read_text(encoding="utf-8").splitlines() if w.strip() and not w.startswith("#")]
    pats = list(PRIVACY) + [(f"the word '{w}'", re.compile(r"\b" + re.escape(w) + r"\b", re.I)) for w in words]
    for p in files:
        rel = p.relative_to(root).as_posix()
        if rel.startswith("site/vendor/") or rel == "local/privacy-words.txt":
            continue
        text = is_text(p)
        if text is None:
            continue
        for i, line in enumerate(text.split("\n"), 1):
            for label, rx in pats:
                m = rx.search(line)
                if m and not (label == "an e-mail address" and m.group(0).lower().startswith("noreply@")):
                    fail(f"Privacy: {rel}:{i} has {label}.")


COUNT_RX = re.compile(r"<!--count:(\w+)-->(.*?)<!--/count-->")


def check_doc_counts(files, root, st, fix):
    for p in files:
        if p.suffix.lower() not in (".md", ".txt"):
            continue
        text = is_text(p)
        if text is None or "<!--count:" not in text:
            continue
        rel = p.relative_to(root).as_posix()

        def rep(m):
            k = m.group(1)
            if k not in st:
                fail(f"Docs: {rel} has unknown count '{k}'.")
                return m.group(0)
            want = f"{st[k]:,}"
            if m.group(2) != want:
                if fix:
                    return f"<!--count:{k}-->{want}<!--/count-->"
                fail(f"Docs: {rel} says {k} is {m.group(2)} but the data says {want}.")
            return m.group(0)

        new = COUNT_RX.sub(rep, text)
        if fix and new != text:
            p.write_text(new, encoding="utf-8", newline="")
            print(f"Fixed counts in {rel}")


LINK_RX = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)|!\[[^\]]*\]\(([^)\s]+)\)")
FENCE_RX = re.compile(r"```.*?```", re.S)


def check_md_links(files, root):
    for p in files:
        if p.suffix.lower() != ".md" or p.relative_to(root).as_posix().startswith("site/vendor/"):
            continue
        text = is_text(p)
        if text is None:
            continue
        text = FENCE_RX.sub(lambda m: "\n" * m.group(0).count("\n"), text)
        for i, line in enumerate(text.split("\n"), 1):
            line = re.sub(r"`[^`]*`", "", line)
            for m in LINK_RX.finditer(line):
                t = (m.group(1) or m.group(2)).strip("<>")
                if re.match(r"^([a-z][a-z0-9+.-]*:|#|//)", t, re.I):
                    continue
                path = t.split("#")[0].split("?")[0]
                if path and not (p.parent / path).exists():
                    fail(f"Link: {p.relative_to(root).as_posix()}:{i} points to '{t}', which does not exist.")


CONTRIB_URL_RE = re.compile(r"^https://[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/[A-Za-z0-9._~%!$&'()*+,;=:@/?#-]*)?$")


def check_contrib(doc):
    """Check contrib/hand-links.yaml. Returns a summary string, or None when the file is absent."""
    p = ROOT / "contrib" / "hand-links.yaml"
    if not p.exists():
        return None
    try:
        import yaml
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"Contrib: cannot read {p.name}: {type(e).__name__}")
        return None
    if not isinstance(d, dict) or set(d) != {"version", "add_edges", "remove_edges"}:
        fail("Contrib: the file must have exactly the keys version, add_edges and remove_edges.")
        return None
    if d["version"] != 1 or isinstance(d["version"], bool):
        fail("Contrib: version must be 1.")
    names = {n["key"]: n["name"] for n in doc["nodes"]}
    doc_pairs = {(l["child"], l["parent"]) for l in doc["links"]}
    want = ("child", "child_name", "parent", "parent_name", "source_url", "issue")
    pairs = {}
    for lst in ("add_edges", "remove_edges"):
        items = d[lst]
        if not isinstance(items, list):
            fail(f"Contrib: {lst} must be a list.")
            return None
        seen = []
        for i, e in enumerate(items):
            w = f"Contrib: {lst}[{i}]"
            if not isinstance(e, dict) or set(e) != set(want):
                fail(f"{w} must have exactly the keys {', '.join(want)}.")
                continue
            if not all(isinstance(e[k], str) for k in want[:5]) or not isinstance(e["issue"], int) \
                    or isinstance(e["issue"], bool) or e["issue"] < 1:
                fail(f"{w} has a value of the wrong type (issue must be a positive integer).")
                continue
            for k, nk in (("child", "child_name"), ("parent", "parent_name")):
                if e[k] not in names:
                    fail(f"{w} {k} '{e[k]}' is not a node.")
                elif e[nk] != names[e[k]]:
                    fail(f"{w} {nk} does not match the node name.")
            if len(e["source_url"]) > 300 or not CONTRIB_URL_RE.fullmatch(e["source_url"]):
                fail(f"{w} has a source_url that is not a plain https link.")
            if e["child"] == e["parent"]:
                fail(f"{w} links a node to itself.")
            seen.append((e["child"], e["parent"]))
        if len(set(seen)) != len(seen):
            fail(f"Contrib: {lst} has a duplicate (child, parent) pair.")
        if seen != sorted(seen):
            fail(f"Contrib: {lst} is not sorted by (child, parent).")
        pairs[lst] = set(seen)
    edges = (doc_pairs | pairs["add_edges"]) - pairs["remove_edges"]
    up = defaultdict(list)
    for c, pa in edges:
        up[c].append(pa)
    state = {}
    cyc = None
    for root in list(up):
        if root in state or cyc:
            continue
        state[root] = 1
        stack = [(root, iter(up[root]))]
        while stack and not cyc:
            n, it = stack[-1]
            for m in it:
                if state.get(m) == 1:
                    cyc = m
                    break
                if m not in state:
                    state[m] = 1
                    stack.append((m, iter(up.get(m, ()))))
                    break
            else:
                state[n] = 2
                stack.pop()
    if cyc:
        fail(f"Contrib: the links make a cycle through '{cyc}'.")
    have = len(pairs["add_edges"] & doc_pairs)
    return f"contrib: add {len(pairs['add_edges'])} ({have} already in the data), remove {len(pairs['remove_edges'])}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=str(ROOT / "data" / "taxonomy.json"), help="data file to check")
    ap.add_argument("--fix-counts", action="store_true", help="rewrite count markers in docs")
    a = ap.parse_args()
    dp = Path(a.data)
    try:
        doc = json.loads(dp.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"FAIL: cannot read {dp}: {e}")
        return 1
    contrib_line = None
    if check_schema(doc):
        pp = dp.parent / "proposals.csv"           # the review list sits beside the data file, outside the schema
        if pp.exists():
            with open(pp, encoding="utf-8", newline="") as f:
                doc["proposals"] = list(csv.DictReader(f))
        st = check_integrity(doc, dp)
        contrib_line = check_contrib(doc)
    else:
        st = None
    files = git_files(ROOT)
    check_privacy(files, ROOT)
    if st:
        check_doc_counts(files, ROOT, st, a.fix_counts)
    check_md_links(files, ROOT)
    if errors:
        for e in errors:
            print("FAIL:", e)
        print(f"{len(errors)} problem(s) found.")
        return 1
    print("OK: schema, integrity, contrib, CSV, privacy, doc counts and links all pass.")
    if contrib_line:
        print("  " + contrib_line)
    if st:
        print("  " + ", ".join(f"{k} {v}" for k, v in st.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
