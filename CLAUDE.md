# Agent instructions

Instructions for Claude Code and other LLM agents in this repo. Human contributors: see [CONTRIBUTING.md](CONTRIBUTING.md).

## Public by default

- Treat every file, commit message and code comment as public.
- Follow the [privacy rules](CONTRIBUTING.md#privacy-rules). Add no personal name, e-mail address, home path, host name or network address.
- Put private notes in `local/`. It is git-ignored. Never copy them into tracked files.
- Add no data from closed sources.

## Data files are generated

- Do not edit `data/taxonomy.json`, `data/*.csv` or `site/` output by hand.
- Run `python tools/build.py --source DIR` to change data. The pipeline that derives the tree is not in this repo.
- Run `uv run --with jsonschema python tools/check.py` before each commit. Fix every failure.

## Writing

- Write in Simplified Technical English. See [CONTRIBUTING.md](CONTRIBUTING.md#writing-rules).
- Write each number from the data as a count marker. Run `check.py --fix-counts` to fill it.
- Claim only what you checked. Say what you did not check.

## Keep the docs in step

- Update `llms.txt` and `CHANGELOG.md` when you add, rename or remove a document.
- Run `python3 tools/llms_full.py` after each document change, then `python3 tools/llms_full.py --check`.

## Git

- Do not commit or push unless the owner asks.
- Push to a branch, wait for CI, then fast-forward `main`.
