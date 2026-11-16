# Changelog

All notable changes to the data, schema, documents and tools. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The data version follows semantic versioning as the [data guide](docs/data-guide.md#versions-and-pinning) describes.

## [1.1.0] - 2026-11-16

More genres have a parent. Isolated genres go down from 481 to <!--count:isolated-->300<!--/count-->, and roots go down from 557 to <!--count:roots-->348<!--/count-->.

### Added

- **MusicBrainz links:** <!--count:links_musicbrainz-->1,603<!--/count--> "subgenre of" links from the MusicBrainz core data dump (CC0).
- **Wikidata ids from MusicBrainz:** a genre whose Wikidata item has no MusicBrainz genre id now takes its Wikidata id from the MusicBrainz side. Wikidata ids go up from 1,655 to <!--count:with_wikidata_id-->2,216<!--/count-->.
- **Two-step Wikidata links:** when the direct Wikidata parent is not a genre in this data set, the build takes the nearest genre two "subclass of" steps up (<!--count:links_medium-->152<!--/count--> links, basis `derived`).
- **Field `confidence`** on each link: `high` (<!--count:links_high-->3,487<!--/count-->), `medium` (<!--count:links_medium-->152<!--/count-->) or `low` (<!--count:links_low-->1,093<!--/count-->). The data guide gives the rule. `links.csv` has it as the last column.
- **Review list:** `data/proposals.csv` holds <!--count:proposals-->212<!--/count--> possible parents three or four Wikidata steps up. They are not links.

### Changed

- **Schema 1.1.0:** `confidence` is a required link field.
- **Counts:** <!--count:links-->4,732<!--/count--> links, <!--count:aliases-->3,002<!--/count--> aliases, <!--count:tag_level-->136<!--/count--> tag-level genres.

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

[1.1.0]: https://github.com/UniversalSyntropy/music-genre-taxonomy/releases/tag/v1.1.0
[1.0.0]: https://github.com/UniversalSyntropy/music-genre-taxonomy/releases/tag/v1.0.0
