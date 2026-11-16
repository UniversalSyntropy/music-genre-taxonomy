# Data guide

This guide shows how to read the genre taxonomy files in code. It lists every field and gives short recipes for the common tasks. For the origin of the data, see [Sources](sources.md).

The data is a directed acyclic graph (DAG) of <!--count:nodes-->2,453<!--/count--> genres. A genre can have more than one parent, so it is not a strict tree.

## Files

| File | Holds | Use it for |
| --- | --- | --- |
| [`data/taxonomy.json`](../data/taxonomy.json) | Everything: header, sources, nodes, links, aliases | Code. This is the main file. |
| [`data/nodes.csv`](../data/nodes.csv) | One row per genre, with ids and a `parents` column | Spreadsheets |
| [`data/links.csv`](../data/links.csv) | One row per parent link | Spreadsheets, SQL import |
| [`data/aliases.csv`](../data/aliases.csv) | One row per name spelling | Tag matching |
| [`schema/taxonomy.schema.json`](../schema/taxonomy.schema.json) | JSON Schema (draft 2020-12) for the JSON file | Validation |

The CSV files hold the same rows as the JSON file. `tools/check.py` tests that the row counts match.

## Top-level fields

| Field | Type | Meaning |
| --- | --- | --- |
| `$schema` | string | URL of the schema |
| `name` | string | Always `Music Genre Taxonomy` |
| `schema_version` | string | Semantic version of the file layout |
| `version` | string | Semantic version of the data |
| `tree_version` | string | 12-character content hash from the build |
| `licence` | string | SPDX id of the whole file: `CC-BY-4.0` |
| `counts` | object | `nodes`, `links`, `aliases`, `tag_level`. They equal the array lengths. |
| `sources` | array | One entry per source (see below) |
| `nodes`, `links`, `aliases` | arrays | The data |

## Nodes

One node is one genre.

| Field | Type | Meaning |
| --- | --- | --- |
| `key` | string | Stable id. Lowercase letters and digits in any script, joined by single hyphens. Example: `acid-house`. |
| `name` | string | Display name in simple title case |
| `tag_level` | boolean | `true` if the genre is a good value for a file's genre tag. `false` for a genre that is broader (for example Electronic) or narrower than that depth. |
| `source` | string | Code of the source that gave the genre first |
| `licence` | string | SPDX id of this row |
| `seen_in` | array | Codes of every source that lists the genre |
| `external.musicbrainz_id` | string | MusicBrainz genre id (UUID). Left out if unknown. |
| `external.wikidata_id` | string | Wikidata item id, such as `Q341364`. Left out if unknown. |
| `external.discogs_name` | string | Name in the Discogs data. Left out if unknown. |
| `external.discogs_kind` | string | `genre` or `style`, as Discogs lists it |

The `nodes.csv` file adds a `parents` column with the parent keys.

## Links

One link says "child is a sub-genre of parent". Every link carries its source and evidence.

| Field | Type | Meaning |
| --- | --- | --- |
| `child` | string | Key of the narrower genre |
| `parent` | string | Key of the broader genre |
| `relation` | string | Always `subgenre_of` |
| `source` | string | Code of the source that gave the link: `wikidata`, `musicbrainz`, `discogs` or `hand` (a checked link that cites its page in `evidence`) |
| `licence` | string | SPDX id of this row |
| `basis` | string | `sourced`: the source states the link. `derived`: this repo computed it from source data. |
| `confidence` | string | `high`, `medium` or `low`. See the rule below. Added in schema 1.1.0. |
| `evidence` | string | Text that shows why the link exists |

Evidence examples:

- `wikidata Q341364 subclass of Q20502`: a Wikidata statement.
- `wikidata Q30 subclass of Q31 subclass of Q2`: a chain of two Wikidata statements. The middle item is not a genre in this data set.
- `musicbrainz <child id> subgenre of <parent id>`: a MusicBrainz relationship, with both MusicBrainz genre ids.
- `co-occurrence 1.00 of 26187 releases`: a Discogs style and genre occur together on nearly all releases in the dump.

Confidence rule. The value follows from `source` and `basis` only. It does not count sources.

| Confidence | Links | Rule |
| --- | --- | --- |
| `high` | <!--count:links_high-->3,508<!--/count--> | A source states the link: Wikidata one step, MusicBrainz "subgenre of", or a hand link that cites the page |
| `medium` | <!--count:links_medium-->152<!--/count--> | A chain of two Wikidata "subclass of" statements |
| `low` | <!--count:links_low-->1,093<!--/count--> | A statistic: Discogs co-occurrence. Co-occurrence does not state a hierarchy |

## Proposals

[`data/proposals.csv`](../data/proposals.csv) lists <!--count:proposals-->212<!--/count--> possible parents that are not links. Each row is a genre in this data set three or four Wikidata "subclass of" steps up. Columns: `child`, `parent`, `depth`, `evidence`. Use the file as a review list. Do not read it as a parent link.

The same child and parent pair can come from two sources. That gives two link rows. Count distinct parents, not rows.

## Aliases

An alias is one spelling of a genre name. Use aliases to match free-text tag values to a node.

| Field | Type | Meaning |
| --- | --- | --- |
| `name` | string | The spelling as the source writes it |
| `normal` | string | The normal form of the name (see below) |
| `node` | string | Key of the genre |
| `source` | string | `musicbrainz`, `discogs` or `hand` |
| `licence` | string | SPDX id of this row |

Three aliases are hand-made: `Goa` to `goa-trance`, `Drum n Bass` to `drum-and-bass` and `House Music` to `house`. They carry the licence CC-BY-4.0.

In this release no normal form points to two nodes. Do not rely on that for later releases: handle a list of nodes per normal form.

## Sources

Each entry in `sources` holds `code`, `name`, `url`, `licence`, `licence_url` and `retrieved`. The `retrieved` field says when the source was read. See [Sources](sources.md) for the values.

## Normal form for alias lookup

Compute the normal form of your input, then look it up in the `normal` field of the aliases. The steps are:

1. Apply Unicode NFKC.
2. Fold the case.
3. Replace `&` with ` and `.
4. Keep only letters and digits, in any script.

Example: `Drum & Bass` becomes `drumandbass`.

Python:

```python
import unicodedata

def normal(name: str) -> str:
    s = unicodedata.normalize("NFKC", name).casefold().replace("&", " and ")
    return "".join(ch for ch in s if ch.isalnum())

print(normal("Drum & Bass"))
```

JavaScript:

```javascript
const normal = (name) =>
  [...name.normalize("NFKC").toLowerCase().replaceAll("&", " and ")]
    .filter((c) => /[\p{L}\p{N}]/u.test(c))
    .join("");

console.log(normal("Drum & Bass"));
```

> **Note:** Python `casefold()` and JavaScript `toLowerCase()` differ for a few characters, such as the German sharp s. The data was built with Python. For exact results in JavaScript, test your input against the alias list.

## Walk recipes

All recipes use these two lookups. Build them once.

```python
import json
from collections import defaultdict, deque

data = json.load(open("data/taxonomy.json", encoding="utf-8"))
nodes = {n["key"]: n for n in data["nodes"]}
parents, children = defaultdict(set), defaultdict(set)
for link in data["links"]:
    parents[link["child"]].add(link["parent"])
    children[link["parent"]].add(link["child"])
alias_to_node = defaultdict(set)
for a in data["aliases"]:
    alias_to_node[a["normal"]].add(a["node"])
```

Children of a genre:

```python
print(sorted(children["house"]))
```

All ancestors of a genre (every parent, grandparent and so on):

```python
def ancestors(key):
    seen, queue = set(), deque([key])
    while queue:
        for p in parents[queue.popleft()]:
            if p not in seen:
                seen.add(p)
                queue.append(p)
    return seen

print(sorted(ancestors("acid-house")))
```

The tag-level ancestor: walk the parents breadth-first until a node has `tag_level` true. A tag-level node returns itself. Sort the parents so the result is the same each time.

```python
def tag_level_ancestor(key):
    seen, queue = {key}, deque([key])
    while queue:
        k = queue.popleft()
        if nodes[k]["tag_level"]:
            return k
        for p in sorted(parents[k]):
            if p not in seen:
                seen.add(p)
                queue.append(p)
    return None

print(tag_level_ancestor("2-step"))
```

Resolve a tag value to genres. The function returns a list because a later release can map one spelling to several genres.

```python
def normal(name):
    import unicodedata
    s = unicodedata.normalize("NFKC", name).casefold().replace("&", " and ")
    return "".join(ch for ch in s if ch.isalnum())

print(sorted(alias_to_node[normal("Drum n Bass")]))
```

The function returns `None` when no ancestor is tag-level.

## DAG caveats

- **Many parents:** <!--count:multi_parent-->863<!--/count--> genres have two or more distinct parents. A tree drawing shows each genre once, under one parent. The viewer picks the nearest parent. The data keeps all parents.
- **Roots:** <!--count:roots-->331<!--/count--> genres have no parent. <!--count:isolated-->282<!--/count--> of them have no child either.
- **No cycles:** `tools/check.py` tests that the graph has no cycle.
- **Duplicate rows:** a pair from two sources has two rows. Use a set of parents.

## Map to SKOS and schema.org

The data file is not SKOS. SKOS cannot hold the source, licence, basis and evidence of each link without reification. The table shows how the fields map if you want to convert.

| This data | SKOS |
| --- | --- |
| Whole file | `skos:ConceptScheme` |
| Node | `skos:Concept` |
| `name` | `skos:prefLabel` |
| Alias | `skos:altLabel` |
| Link `subgenre_of` (child to parent) | `skos:broader` |
| `external` ids | `skos:exactMatch` |

The website emits `Dataset` and `DefinedTerm` JSON-LD for search engines. The data file is not schema.org. `DefinedTermSet` has no parent relation and no per-link provenance.

## Versions and pinning

| Field | Rule |
| --- | --- |
| `schema_version` | Semantic version of the file layout. Changes when the shape of the file changes. |
| `version` | Semantic version of the data. Major: a key is removed or renamed, or the schema breaks. Minor: nodes, links or aliases are added. Patch: corrections. |
| `tree_version` | Content hash from the build. It changes when the content changes. |

Keys are stable and never reused. A key you store today still names the same genre later, unless a major release says otherwise.

To pin a version, read the file at a git tag and compare `tree_version`. Both URLs below give version 1.0.0.

- `https://cdn.jsdelivr.net/gh/UniversalSyntropy/music-genre-taxonomy@v1.0.0/data/taxonomy.json`
- `https://raw.githubusercontent.com/UniversalSyntropy/music-genre-taxonomy/v1.0.0/data/taxonomy.json`

## Changelog rule

Every release adds an entry to [CHANGELOG.md](../CHANGELOG.md) with the new `version`, the counts and the `tree_version`. A removed or renamed key is always listed there.
