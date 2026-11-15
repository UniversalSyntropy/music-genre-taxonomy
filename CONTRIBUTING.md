# Contributing

You can report a wrong link or a missing genre without writing code. This page says how, what a good report holds and which rules apply to changes.

## Report a wrong link or a missing genre

Use an issue form:

- [Wrong link](https://github.com/UniversalSyntropy/music-genre-taxonomy/issues/new?template=wrong-link.yml): a genre has a parent that is wrong, or lacks one.
- [Missing genre](https://github.com/UniversalSyntropy/music-genre-taxonomy/issues/new?template=missing-genre.yml): a genre or a name spelling is not in the data.

A good report holds:

- **The genre key**, for example `acid-house`. The viewer shows it in the address as `?g=<key>`.
- **What is wrong**, in one or two sentences.
- **A public source URL** that supports your claim. A Wikipedia page, a Wikidata item or a MusicBrainz page is a good source.

## Fix it upstream first

Many links come from Wikidata and the genre list comes from MusicBrainz. A fix there helps every user of those sources. The next build of this repo takes the fix.

| Problem | Where to fix it first |
| --- | --- |
| Wrong "subclass of" link | The Wikidata item. Edit the "subclass of" statement and cite a source. |
| Missing or misspelled genre name | MusicBrainz. Ask its community. I did not check who can edit the genre list there. |
| Wrong Discogs link or missing alias | This repo. Open an issue. |

Open an issue here as well. A maintainer can then check the next build. If upstream does not take the fix, say so in the issue.

## Privacy rules

Treat the repo as public. Git history is permanent.

- **No personal data:** no names, e-mail addresses, home paths, host names, network addresses or account details in files, commit messages or code comments.
- **No data from closed sources:** do not add data from Rate Your Music, Spotify lists or any other source that is not open. Name a source with an open licence for every row.
- **No private collection data:** do not add file names, tag values or counts from your own music library.

`python tools/check.py` scans tracked and new files for common personal-data patterns. Put your own words to block in `local/privacy-words.txt`, one on each line. The file is git-ignored.

## Writing rules

Write documents in Simplified Technical English. This is a short form of the rules.

- **Short sentences:** 25 words at most. Steps 20 words at most.
- **One idea each:** one idea in each sentence and each paragraph.
- **Active voice:** "The tool checks the links", not "The links are checked".
- **One word for one thing:** do not swap synonyms. Use "genre", "link", "alias" and "key" as the [data guide](docs/data-guide.md) uses them.
- **Answer first:** put the result before the reason.
- **Tables:** use a table for structured facts.
- **No marketing words:** no superlatives and no claims you did not check.

## Numbers in documents

Write each count from the data as a count marker, for example `<!--count:nodes-->2,450<!--/count-->`. The check tool compares the marker text with the data. To refresh the markers after a build, run:

```bash
uv run --with jsonschema python tools/check.py --fix-counts
```

Supported names: `nodes`, `links`, `aliases`, `tag_level`, `roots`, `isolated`, `multi_parent`, `nodes_musicbrainz`, `nodes_discogs`, `links_wikidata`, `links_discogs`, `with_musicbrainz_id`, `with_wikidata_id`, `with_discogs_name`.

## Data files are generated

Do not edit `data/taxonomy.json` or the CSV files by hand. `tools/build.py` writes them from the pipeline output. A fix to a link goes into the pipeline input, then you build again.

## Run the checks

Run these commands before each push. The first one needs `jsonschema`.

```bash
uv run --with jsonschema python tools/check.py
python3 tools/llms_full.py --check
```

If `llms_full.py --check` fails, run `python3 tools/llms_full.py` and commit `llms-full.txt`.

## Push rule

1. Push your change to a branch. Do not push to `main`.
2. Wait for CI to pass.
3. Fast-forward `main` to the branch.

## Update the docs with the change

When you add, rename or remove a document, update `llms.txt` and `CHANGELOG.md` in the same change. Fix a broken link in the same commit that breaks it.

## Licence of contributions

By contributing, you agree that your documents and data are licensed under [CC BY 4.0](LICENSE-docs) and your code under the [MIT licence](LICENSE). Credit goes to "music-genre-taxonomy contributors". Do not add personal names to licence or copyright lines.
