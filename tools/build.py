#!/usr/bin/env python3
"""Build the public taxonomy files from a source directory.

Usage: python tools/build.py --source DIR [--version X.Y.Z] [--out DIR]
The source dir may also come from the env var GENRE_SOURCE_DIR.
Needs: pyyaml. Output is deterministic: same input, same bytes.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import yaml

SCHEMA_ID = "https://universalsyntropy.github.io/music-genre-taxonomy/schema/taxonomy.schema.json"
SCHEMA_VERSION = "1.1.0"
REPO_URL = "https://github.com/UniversalSyntropy/music-genre-taxonomy"
SPDX = {"CC0": "CC0-1.0"}
SPDX_URL = {
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
}
SOURCE_INFO = {
    "discogs": ("Discogs data dumps (genres and styles)", "https://data.discogs.com/"),
    "musicbrainz": ("MusicBrainz genres and genre relationships (core data dump)", "https://musicbrainz.org/doc/MusicBrainz_Database/Download"),
    "wikidata": ("Wikidata subclass-of statements", "https://www.wikidata.org/"),
    "hand": ("Hand-added aliases", REPO_URL),
}
HAND_LICENCE = "CC-BY-4.0"
# Link confidence from (source, basis). high: a source states the link. medium: a short chain of stated links (Wikidata, 2 steps).
# low: a statistic (Discogs co-occurrence), which is no statement of hierarchy.
CONFIDENCE = {("wikidata", "sourced"): "high", ("musicbrainz", "sourced"): "high", ("hand", "sourced"): "high",
              ("wikidata", "derived"): "medium", ("discogs", "derived"): "low"}
PROPOSAL_COLS = ["child", "parent", "depth", "evidence"]


def normal(name: str) -> str:
    """Normal form: NFKC, case fold, '&' to 'and', keep only letters and digits."""
    s = unicodedata.normalize("NFKC", name).casefold().replace("&", " and ")
    return "".join(ch for ch in s if ch.isalnum())


def spdx(lic: str) -> str:
    return SPDX.get(lic, lic)


def load_yaml(p: Path):
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(p: Path):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def qnum(q: str) -> int:
    return int(q[1:])


def build(src: Path):
    tree = load_yaml(src / "data" / "tree.yaml")
    ali = load_yaml(src / "data" / "aliases.yaml")["aliases"]
    inputs = {i["code"]: i for i in load_yaml(src / "data" / "inputs" / "inputs.yaml")["inputs"]}
    mbg = load_json(src / "data" / "inputs" / "musicbrainz-genres.json")["genres"]
    wd = load_json(src / "data" / "inputs" / "wikidata-subclass.json")["edges"]
    dg = load_json(src / "data" / "inputs" / "discogs-genres.json")
    rel_path = src / "data" / "inputs" / "musicbrainz-relations.json"
    mb_wd = load_json(rel_path)["wikidata"] if rel_path.exists() else []
    prop_path = src / "data" / "proposals.yaml"
    props = (load_yaml(prop_path) or {}).get("proposals", []) if prop_path.exists() else []
    stats = defaultdict(int)

    def ok(code):
        return bool(inputs.get(code, {}).get("publishable"))

    # --- filter by privacy rules
    nodes_in = [n for n in tree["nodes"] if ok(n["source"])]
    keys = {n["key"] for n in nodes_in}
    stats["nodes_dropped"] = len(tree["nodes"]) - len(nodes_in)
    edges_in = [e for e in tree["edges"] if ok(e["source"]) and e["child"] in keys and e["parent"] in keys]
    stats["links_dropped"] = len(tree["edges"]) - len(edges_in)
    ali_in = [a for a in ali if a["source"] != "filetag" and ok(a["source"]) and a["node"] in keys]
    stats["aliases_dropped"] = len(ali) - len(ali_in)

    # --- external ids
    name_to_node = {}  # exact MusicBrainz name -> node (via alias row)
    for a in ali:
        if a["source"] == "musicbrainz":
            name_to_node[a["name"]] = a["node"]
    node_by_normal = defaultdict(list)
    for n in nodes_in:
        node_by_normal[normal(n["name"])].append(n["key"])
    node_name = {n["key"]: n["name"] for n in nodes_in}

    mb_cand = defaultdict(list)  # node -> [(id, name)]
    unmatched_mb = 0
    for g in mbg:
        k = name_to_node.get(g["name"])
        if k is None:
            c = node_by_normal.get(normal(g["name"]), [])
            k = c[0] if len(c) == 1 else None
        if k is None or k not in keys:
            unmatched_mb += 1
            continue
        mb_cand[k].append((g["id"], g["name"]))
    stats["mb_genres_unmatched"] = unmatched_mb
    mb_id = {}
    for k, c in mb_cand.items():
        if len(c) > 1:
            stats["mb_conflicts"] += 1
        c.sort(key=lambda x: (x[1].casefold() != node_name[k].casefold(), x[0]))
        mb_id[k] = c[0][0]

    mb_to_q = defaultdict(set)
    for e in wd:
        mb_to_q[e["child_mb"]].add(e["child_qid"])
        mb_to_q[e["parent_mb"]].add(e["parent_qid"])
    mb_link_q = defaultdict(set)  # MusicBrainz genre -> Wikidata item, from the MusicBrainz side (used when P8052 gives none)
    for r in mb_wd:
        mb_link_q[r["mb"]].add(r["qid"])
    wd_id = {}
    for k, i in mb_id.items():
        qs = mb_to_q.get(i) or mb_link_q.get(i)
        if qs:
            if len(qs) > 1:
                stats["wd_conflicts"] += 1
            wd_id[k] = min(qs, key=qnum)

    disc = {}  # normal -> (name, kind); genre wins over style
    for s in dg["styles"]:
        disc.setdefault(normal(s["name"]), (s["name"], "style"))
    for g in dg["genres"]:
        disc[normal(g["name"])] = (g["name"], "genre")
    disc_exact = {s["name"] for s in dg["styles"]} | {g["name"] for g in dg["genres"]}
    disc_alias = defaultdict(list)
    for a in ali_in:
        if a["source"] == "discogs" and a["name"] in disc_exact:
            disc_alias[a["node"]].append(a["name"])
    disc_id = {}
    for n in nodes_in:
        k = n["key"]
        hit = None
        cands = sorted(set(disc_alias.get(k, [])))
        for nm in cands:
            hit = disc[normal(nm)]
            break
        if hit is None:
            hit = disc.get(normal(n["name"]))
        if hit:
            disc_id[k] = hit
        if len(cands) > 1:
            stats["discogs_conflicts"] += 1

    # --- rows
    used = set()
    nodes = []
    for n in sorted(nodes_in, key=lambda n: n["key"]):
        k = n["key"]
        seen = sorted(s for s in n["seen_in"] if ok(s))
        used.update(seen)
        used.add(n["source"])
        ext = {}
        if k in mb_id:
            ext["musicbrainz_id"] = mb_id[k]
        if k in wd_id:
            ext["wikidata_id"] = wd_id[k]
        if k in disc_id:
            ext["discogs_name"], ext["discogs_kind"] = disc_id[k]
        nodes.append({"key": k, "name": n["name"], "tag_level": bool(n["tag_level"]), "source": n["source"],
                      "licence": HAND_LICENCE if n["source"] == "hand" else spdx(n["licence"]), "seen_in": seen, "external": ext})
    links = []
    for e in sorted(edges_in, key=lambda e: (e["child"], e["parent"], e["source"])):
        used.add(e["source"])
        hand = e["source"] == "hand"   # a hand link cites a page that states it, so its basis is sourced; own rows are CC BY 4.0
        basis = "sourced" if hand else e["basis"]
        links.append({"child": e["child"], "parent": e["parent"], "relation": e["relation"], "source": e["source"],
                      "licence": HAND_LICENCE if hand else spdx(e["licence"]), "basis": basis, "confidence": CONFIDENCE[(e["source"], basis)],
                      "evidence": e["evidence"]})
    aliases = []
    for a in ali_in:
        used.add(a["source"])
        lic = HAND_LICENCE if a["source"] == "hand" else spdx(a["licence"])
        aliases.append({"name": a["name"], "normal": a["normal"], "node": a["node"], "source": a["source"], "licence": lic})
    aliases.sort(key=lambda a: (a["normal"], a["name"], a["node"]))

    sources = []
    for code in sorted(used):
        if code not in SOURCE_INFO:
            raise SystemExit(f"Unknown source code in published rows: {code}")
        nm, url = SOURCE_INFO[code]
        inp = inputs[code]
        lic = HAND_LICENCE if code == "hand" else spdx(inp["licence"])
        sources.append({"code": code, "name": nm, "url": url, "licence": lic, "licence_url": SPDX_URL[lic],
                        "retrieved": str(inp["retrieved"])})
    proposals = sorted(({c: r[c] for c in PROPOSAL_COLS} for r in props if r["child"] in keys and r["parent"] in keys),
                       key=lambda r: (r["child"], r["parent"]))
    return {
        "tree_version": str(tree["tree_version"]), "nodes": nodes, "links": links, "aliases": aliases, "proposals": proposals,
        "sources": sources, "stats": dict(stats), "mb_unmatched": unmatched_mb,
    }


def dump(o) -> str:
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"), sort_keys=False)


def write_json(path: Path, doc: dict, version: str):
    head = {
        "$schema": SCHEMA_ID, "name": "Music Genre Taxonomy", "schema_version": SCHEMA_VERSION, "version": version,
        "tree_version": doc["tree_version"], "licence": "CC-BY-4.0",
        "counts": {"nodes": len(doc["nodes"]), "links": len(doc["links"]), "aliases": len(doc["aliases"]),
                   "tag_level": sum(1 for n in doc["nodes"] if n["tag_level"])},
    }
    lines = ["{"]
    for k, v in head.items():
        lines.append(f" {json.dumps(k)}:{dump(v)},")
    for sec in ("sources", "nodes", "links", "aliases"):
        lines.append(f' "{sec}":[')
        rows = [dump(r) for r in doc[sec]]
        lines.append(",\n".join(rows))
        lines.append(" ]" + ("," if sec != "aliases" else ""))
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_csv(path: Path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def check_contrib_copy(src: Path, repo_root: Path):
    """The plugin must build the tree with the public contrib file. Exit with the fix if the copy is stale."""
    pub = repo_root / "contrib" / "hand-links.yaml"
    copy = src / "data" / "contrib.yaml"
    pub_bytes = pub.read_bytes() if pub.exists() else None
    entries = 0
    if pub_bytes is not None:
        d = yaml.safe_load(pub_bytes.decode("utf-8")) or {}
        entries = len(d.get("add_edges") or []) + len(d.get("remove_edges") or [])
    fix = f"cp contrib/hand-links.yaml {src}/data/contrib.yaml, then rebuild the tree in the pipeline."
    if copy.exists():
        if copy.read_bytes() != pub_bytes:
            sys.exit(f"error: {copy} differs from contrib/hand-links.yaml. Fix: {fix}")
    elif entries:
        sys.exit(f"error: contrib/hand-links.yaml has {entries} entries but {copy} is missing. Fix: {fix}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=os.environ.get("GENRE_SOURCE_DIR"), help="source dir (or env GENRE_SOURCE_DIR)")
    ap.add_argument("--version", help="data version X.Y.Z (default: keep current, else 1.0.0)")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "data"), help="output dir")
    a = ap.parse_args()
    if not a.source:
        ap.error("give --source DIR or set GENRE_SOURCE_DIR")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    version = a.version
    if not version:
        version = "1.0.0"
        cur = out / "taxonomy.json"
        if cur.exists():
            try:
                version = load_json(cur)["version"]
            except Exception:
                pass
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        ap.error("version must look like 1.2.3")

    check_contrib_copy(Path(a.source), Path(__file__).resolve().parent.parent)
    d = build(Path(a.source))
    write_json(out / "taxonomy.json", d, version)
    parents = defaultdict(list)
    for l in d["links"]:
        parents[l["child"]].append(l["parent"])
    write_csv(out / "nodes.csv",
              ["key", "name", "tag_level", "source", "licence", "seen_in", "musicbrainz_id", "wikidata_id",
               "discogs_name", "discogs_kind", "parents"],
              [[n["key"], n["name"], "true" if n["tag_level"] else "false", n["source"], n["licence"],
                "|".join(n["seen_in"]), n["external"].get("musicbrainz_id", ""), n["external"].get("wikidata_id", ""),
                n["external"].get("discogs_name", ""), n["external"].get("discogs_kind", ""),
                "|".join(sorted(set(parents[n["key"]])))] for n in d["nodes"]])
    link_cols = ("child", "parent", "relation", "source", "licence", "basis", "evidence", "confidence")   # new column last: old readers keep working
    write_csv(out / "links.csv", list(link_cols), [[l[c] for c in link_cols] for l in d["links"]])
    write_csv(out / "proposals.csv", PROPOSAL_COLS, [[r[c] for c in PROPOSAL_COLS] for r in d["proposals"]])
    write_csv(out / "aliases.csv", ["name", "normal", "node", "source", "licence"],
              [[x[c] for c in ("name", "normal", "node", "source", "licence")] for x in d["aliases"]])

    N = d["nodes"]
    print(f"nodes {len(N)}  links {len(d['links'])}  aliases {len(d['aliases'])}  "
          f"tag_level {sum(n['tag_level'] for n in N)}  proposals {len(d['proposals'])}  version {version}")
    print(f"dropped: nodes {d['stats'].get('nodes_dropped', 0)}, links {d['stats'].get('links_dropped', 0)}, "
          f"aliases {d['stats'].get('aliases_dropped', 0)}")
    for kind in ("musicbrainz_id", "wikidata_id", "discogs_name"):
        c = sum(1 for n in N if kind in n["external"])
        print(f"with {kind}: {c} of {len(N)}")
    print(f"MusicBrainz genres with no node: {d['mb_unmatched']}")
    for k in ("mb_conflicts", "wd_conflicts", "discogs_conflicts"):
        print(f"{k}: {d['stats'].get(k, 0)}")


if __name__ == "__main__":
    sys.exit(main())
