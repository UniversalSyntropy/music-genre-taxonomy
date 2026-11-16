# Changelog

All notable changes to the data, schema, documents and tools. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The data version follows semantic versioning as the [data guide](docs/data-guide.md#versions-and-pinning) describes.

## [1.2.0] - 2026-11-16

### Added

- **New genre Korean Folk** (`korean-folk`, Korean folk music or minsogak, Wikidata Q107000797), under Folk. Aliases "Korean Folk Music" and "Minsogak".
- **Four links under it:** Pansori, Sanjo, Sinawi and Muak. Wikidata gives each as a subclass of Korean folk music.
- **New genres Sampler-based Music and Tracker Music** (Wikidata Q2271846 and Q106423092). The chain is Demostyle, Tracker Music, Sampler-based Music, Bit Music, with one Wikidata "subclass of" statement per link.
- **Two folk links:** Kan Ha Diskan (Wikidata: Breton folk music) and Puirt À Beul (Wikipedia: traditional song of Scotland) go under Folk.

### Changed

- **Counts:** <!--count:nodes-->2,453<!--/count--> genres, <!--count:links-->4,753<!--/count--> links, <!--count:aliases-->3,007<!--/count--> aliases. Isolated genres go down to <!--count:isolated-->282<!--/count-->.

`schema_version` 1.1.0, `version` 1.2.0, `tree_version` `d344f2c9e382`.

## [1.1.1] - 2026-11-16

### Added

- **Hand links:** 11 parent links for 10 isolated genres, with source `hand`. Each one names the Wikipedia or Wikidata page that states it. Candidates came from an AI review of the isolated genres, and each was checked against the cited page. Isolated genres go down from 300 to 289.

### Changed

- **Counts:** 4,743 links; confidence `high` on 3,498.
- **Hand links in the files:** licence CC BY 4.0 and basis `sourced`, the same as the other rows this repo makes. No schema change.

`schema_version` 1.1.0, `version` 1.1.1, `tree_version` `c9b1909cbab4`.

## [1.1.0] - 2026-11-16

More genres have a parent. Isolated genres go down from 481 to 300, and roots go down from 557 to 348.

### Added

- **MusicBrainz links:** 1,603 "subgenre of" links from the MusicBrainz core data dump (CC0).
- **Wikidata ids from MusicBrainz:** a genre whose Wikidata item has no MusicBrainz genre id now takes its Wikidata id from the MusicBrainz side. Wikidata ids go up from 1,655 to 2,216.
- **Two-step Wikidata links:** when the direct Wikidata parent is not a genre in this data set, the build takes the nearest genre two "subclass of" steps up (152 links, basis `derived`).
- **Field `confidence`** on each link: `high` (3,487), `medium` (152) or `low` (1,093). The data guide gives the rule. `links.csv` has it as the last column.
- **Review list:** `data/proposals.csv` holds 212 possible parents three or four Wikidata steps up. They are not links.

### Changed

- **Schema 1.1.0:** `confidence` is a required link field.
- **Counts:** 4,732 links, 3,002 aliases, 136 tag-level genres.

`schema_version` 1.1.0, `version` 1.1.0, `tree_version` `a94079cc6db8`.

## [1.0.0] - 2026-11-15

First public release.

### Added

- **Data:** 2,450 genres, 2,938 parent links and 2,993 aliases in `data/taxonomy.json`, with CSV copies of each table.
- **Tag level:** 135 genres marked as tag-level.
- **Sources:** names from MusicBrainz and Discogs, links from Wikidata and Discogs. Every link has a source, licence, basis and evidence.
- **Ids:** MusicBrainz id on 2,221 genres, Wikidata id on 1,655, Discogs name on 766.
- **Schema:** JSON Schema 1.0.0 in `schema/taxonomy.schema.json`.
- **Viewer:** a web viewer, one static page per genre and website metadata for search engines.
- **Tools:** `tools/build.py`, `tools/check.py`, `tools/build_site.py` and `tools/llms_full.py`.
- **Documents:** README, data guide, sources, viewer guide, disclaimer, contributing guide, `llms.txt`, `llms-full.txt` and `CITATION.cff`.

`schema_version` 1.0.0, `version` 1.0.0, `tree_version` `47461e523d86`.

[1.2.0]: https://github.com/UniversalSyntropy/music-genre-taxonomy/releases/tag/v1.2.0
[1.1.1]: https://github.com/UniversalSyntropy/music-genre-taxonomy/releases/tag/v1.1.1
[1.1.0]: https://github.com/UniversalSyntropy/music-genre-taxonomy/releases/tag/v1.1.0
[1.0.0]: https://github.com/UniversalSyntropy/music-genre-taxonomy/releases/tag/v1.0.0
