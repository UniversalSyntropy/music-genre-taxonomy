# Changelog

All notable changes to the data, schema, documents and tools. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The data version follows semantic versioning as the [data guide](docs/data-guide.md#versions-and-pinning) describes.

## [1.0.0] - 2026-11-15

First public release.

### Added

- **Data:** <!--count:nodes-->2,450<!--/count--> genres, <!--count:links-->2,938<!--/count--> parent links and <!--count:aliases-->2,993<!--/count--> aliases in `data/taxonomy.json`, with CSV copies of each table.
- **Tag level:** <!--count:tag_level-->135<!--/count--> genres marked as tag-level.
- **Sources:** names from MusicBrainz and Discogs, links from Wikidata and Discogs. Every link has a source, licence, basis and evidence.
- **Ids:** MusicBrainz id on <!--count:with_musicbrainz_id-->2,221<!--/count--> genres, Wikidata id on <!--count:with_wikidata_id-->1,655<!--/count-->, Discogs name on <!--count:with_discogs_name-->766<!--/count-->.
- **Schema:** JSON Schema 1.0.0 in `schema/taxonomy.schema.json`.
- **Viewer:** a web viewer, one static page per genre and website metadata for search engines.
- **Tools:** `tools/build.py`, `tools/check.py`, `tools/build_site.py` and `tools/llms_full.py`.
- **Documents:** README, data guide, sources, viewer guide, disclaimer, contributing guide, `llms.txt`, `llms-full.txt` and `CITATION.cff`.

`schema_version` 1.0.0, `version` 1.0.0, `tree_version` `47461e523d86`.

[1.0.0]: https://github.com/UniversalSyntropy/music-genre-taxonomy/releases/tag/v1.0.0
