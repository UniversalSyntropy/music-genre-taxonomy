# Sources

This page says where each row comes from, how the tree is built, what a person made by hand and where the data is weak. The numbers come from [`data/taxonomy.json`](../data/taxonomy.json).

## Source table

| Source | Taken | Licence | Official licence page | Retrieved |
| --- | --- | --- | --- | --- |
| MusicBrainz genres | Genre names (<!--count:nodes_musicbrainz-->1,684<!--/count--> nodes), MusicBrainz ids, name aliases | CC0 | [Data license](https://musicbrainz.org/doc/About/Data_License) | 2026-11-15 |
| Discogs data dumps | Genre and style names (<!--count:nodes_discogs-->766<!--/count--> nodes), co-occurrence links (<!--count:links_discogs-->1,093<!--/count-->), name aliases | CC0 | [Discogs data dumps](https://data.discogs.com/) | 2026-11-15 (dump stamp 20261101) |
| Wikidata | "Subclass of" links (<!--count:links_wikidata-->1,845<!--/count-->), Wikidata ids | CC0 | [Wikidata:Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing) | 2026-11-15 |
| This repo | Compilation, schema, three hand aliases, documents | CC BY 4.0 | [LICENSE-docs](../LICENSE-docs) | 2026-11-15 |

What each licence page says (read on 2026-11-15):

- **MusicBrainz:** "The core data of the database is licensed under the CC0." The MusicBrainz database page lists genres as core data. Tags and genre votes on entities are supplementary data under a non-commercial licence. This repo takes the genre list only, not the votes.
- **Discogs:** "This data is made available under the CC0 No Rights Reserved license."
- **Wikidata:** "All structured data (i.e. the main, Property, Lexeme, and EntitySchema namespaces) is released into the public domain." Wikidata describes this as CC0.

## Attribution

CC0 asks for no credit. This repo gives credit anyway. If you reuse this data, use this line:

> Genre data from [music-genre-taxonomy](https://github.com/UniversalSyntropy/music-genre-taxonomy) by music-genre-taxonomy contributors, licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Built from MusicBrainz, Discogs and Wikidata (CC0).

## How the tree is built

The pipeline that derives the tree is not in this repo. This repo holds the output and the tools that build the public files from it.

1. **Names.** MusicBrainz genres and Discogs genres and styles give the genre names. A genre in both lists is one node.
2. **Links.** Wikidata gives a link when the genre has a "subclass of" statement. Discogs gives a link when a style and a genre occur together on nearly all releases in the dump. The evidence field holds the figure, for example `co-occurrence 1.00 of 26187 releases`.
3. **Ids.** The build matches names to MusicBrainz ids. A Wikidata id comes from the match between a MusicBrainz genre and a Wikidata item. A Discogs name comes from an exact or normal-form match.
4. **Aliases.** Every MusicBrainz and Discogs spelling becomes an alias with its normal form.
5. **Filter.** The build drops any row whose source is not marked as publishable in the input list.
6. **Output.** `python tools/build.py --source DIR` writes the JSON and CSV files. The same input gives the same bytes.

Then run `python tools/check.py` and `python tools/build_site.py`. The check tool tests the schema, the links between rows, the CSV row counts, the document counts and the privacy rules.

## What is made by hand

| Item | What |
| --- | --- |
| Three aliases | `Goa` to `goa-trance`, `Drum n Bass` to `drum-and-bass`, `House Music` to `house`. Source code `hand`. |
| An ignore list | A list of source entries that the pipeline skips. It lives in the private pipeline input. |
| The tag-level rule | A person decided which genres are tag-level. <!--count:tag_level-->135<!--/count--> nodes carry the mark. |

Everything else is computed from the three sources.

## Known limits

- **Names:** the names use simple title case. A name reads `Edm`, not `EDM`.
- **Conflicting parents:** 32 genres have a Wikidata parent and a Discogs parent where no parent is an ancestor of another and none is shared. This repo keeps both.
- **Isolated genres:** <!--count:isolated-->481<!--/count--> genres have no parent and no child.
- **Statistical links:** Discogs links come from co-occurrence on releases. They are not editorial decisions.
- **Wikidata errors:** Wikidata "subclass of" links contain errors. This repo passes them on.
- **Missing aliases:** some common tag spellings have no alias yet.
- **Single tag-level mark:** one rule decides tag-level. Your use case can need a different cut.
- **Opinion:** genre classification is a matter of opinion. See [DISCLAIMER.md](../DISCLAIMER.md).

## Report a wrong link

1. Open the genre in the [viewer](https://universalsyntropy.github.io/music-genre-taxonomy/) and copy its key.
2. Open the [wrong-link form](https://github.com/UniversalSyntropy/music-genre-taxonomy/issues/new?template=wrong-link.yml).
3. Name the link, say what is wrong and give a public source.

If the link comes from Wikidata, fix it in Wikidata first. The next build then takes the fix. See [CONTRIBUTING.md](../CONTRIBUTING.md).
