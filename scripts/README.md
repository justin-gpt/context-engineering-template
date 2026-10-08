# scripts/

The automation half of the template: four small command-line tools, the source adapters
they share, and nothing else. Python 3.11+, dependencies in `requirements.txt` (pyyaml,
requests, jsonschema, pytest). Every file shape they read or write is defined in
`docs/formats.md`; the JSON Schemas in `schemas/json/` are used automatically when present.

```bash
pip install -r requirements.txt
python -m pytest -q                                         # the test suite, from the repo root
python scripts/validate_contract.py templates/contracts/*.yaml
python scripts/canon_sync.py --contract templates/contracts/context-contract.yaml --out export/
python scripts/check_freshness.py export/meta.json --contract templates/contracts/context-contract.yaml
python scripts/scan_sensitive.py .
```

Every script answers `--help` with its full behaviour.

| Script | Purpose | Exit codes |
| --- | --- | --- |
| `validate_contract.py PATH...` | Validate business contracts, client contracts and project manifests | 0 valid · 1 problems · 2 usage |
| `canon_sync.py --contract PATH` | Export the canon into the mirror (`export/`) | 0 synced · 1 gate failed or `--fail-on-warn` with warnings · 2 usage |
| `check_freshness.py META --contract PATH` | Report the two clocks; alert when stale | 0 OK · 2 STALE · 1 unreadable input |
| `scan_sensitive.py [PATH]` | Find secrets, emails, phones, public IPs, denylist terms | 0 clean · 1 findings · 2 usage |

## canon_sync.py

```
python scripts/canon_sync.py --contract PATH [--out DIR] [--source-root PATH]
                             [--previous DIR] [--dry-run] [--fail-on-warn] [--now ISO]
```

1. Loads the contract and validates it: `schemas/json/context-contract.schema.json` (or the
   client schema) when present, plus the built-in structural checks in `validate_contract.py`.
2. Picks the adapter from `source_of_truth` and fetches every page in `canonical_pages`.
3. Runs the validation gates. Any failure exits 1 **before anything is written**, so the
   previous export stays intact:
   - contract invalid;
   - a slug with neither an export nor a `pages_missing` entry;
   - a generated file without its header;
   - a `grounded` page that still contains `[CONFIRM]` or `[YOU DECIDE]`;
   - a markdown page whose frontmatter `slug` / `status` / `owner` disagrees with the contract;
   - a gap tracker CSV with the wrong columns or an unknown `Suggested page` / `Status` value;
   - `meta.json` or `bundle.json` not matching their schemas (when the schemas exist).
4. Collects warnings (printed, stored in `meta.json.warnings`, exit 1 only with `--fail-on-warn`):
   a page exported as a placeholder, a bundle over 150 KiB, a page past its `next_review`
   (frontmatter date, else the contract's), a body line that looks like a restated metric
   value (currency amount, percentage, or "customers"/"logos"/"ARR"/"MRR" next to a number,
   outside code fences and tables).
5. Writes `export/contract.yaml` (verbatim bytes), `export/canon/<slug>.md` (generated header,
   then the page's frontmatter and body), `export/meta.json` and `export/bundle.json`, and
   removes `export/canon/*.md` files whose slug left the contract.

`--dry-run` prints the same summary plus every file it would write and writes nothing.
`--source-root` overrides the contract's `source_root` (handy for a vault checked out
elsewhere). `--now` fixes the run time, which the tests use to make the clocks deterministic.

Relative paths in the contract (`source_root`, `rules.gap_tracker`) resolve against the
current directory first, then the repository root, so running from the repo root always
works.

### The two clocks

`meta.json` carries two timestamps that answer different questions:

- **`generated_at`: when did the content last change?** The sync hashes every page's
  `(slug, status, markdown)` plus the contract text (`content_hash` in `meta.json`). If the
  previous export in `--previous` (default: `--out`) has the same hash, the previous
  `generated_at` is kept; every page header and `bundle.json` stay byte-identical, so a
  nightly run with no changes produces a diff limited to `meta.json`. Consumers cite this
  clock: "canon as of 2026-10-08".
- **`last_synced_at`: when did the sync last succeed?** Always the run time. This is the
  heartbeat `check_freshness.py` compares with `freshness.stale_after_days`. It lives only in
  `meta.json` (not in `bundle.json`) precisely so the bundle does not churn.

The nightly workflow uses the distinction: a moved `generated_at` opens a pull request; a
moved `last_synced_at` alone is committed as a heartbeat with nothing to review.

### Placeholders

A page the adapter cannot read (file missing, Notion 404/403) is still exported, as a file
holding only the header with `| available: false` appended, listed in `meta.json.pages_missing`
and present in `bundle.json` with `available: false` and an empty `markdown`. Consumers see
the gap instead of silently losing a page. It is reported as a warning, so CI runs with
`--fail-on-warn` catch it.

## validate_contract.py

Detects the kind of each file (business contract: `canonical_pages` and no `client_id`;
client contract: `client_id`; manifest: `deployment_id`), validates it against the matching
schema when `schemas/json/` has one, and always runs the structural checks: required keys,
allowed values for `status`, `review`, `visibility`, `risk_class`, `mirror_policy`,
`source_of_truth` and `freshness.sync`, owners present, ISO dates, `next_review` after
`last_reviewed`, 1 to 12 canonical pages, control pages that exist, and no string anywhere in
the file that looks like a credential (`secret_`/`ntn_`, `sk-`, `sk_live`, `ghp_`, `xox`,
`AKIA`, `AIza`, `-----BEGIN`, JWT). Findings are masked in the output. A reference such as
`secret-manager://...` is fine; a value is not.

## check_freshness.py

Reads `export/meta.json`, prints the age of both clocks and `OK` or `STALE`, and exits 2 when
`last_synced_at` is older than the threshold (`--stale-after-days`, else the contract's
`freshness.stale_after_days`, else 7). With `--webhook-env ALERT_WEBHOOK_URL`, a stale result
POSTs `{"status", "last_synced_at", "age_days", "threshold_days"}` to the URL held in that
environment variable; the URL is never printed. Point any incoming-webhook endpoint at it and
map the four fields in the receiving automation.

## scan_sensitive.py

Walks the tree (skipping `.git`, `node_modules`, virtual environments, caches, binary files and
the top-level `export/`) and prints `path:line: kind: text` for secret-looking strings (masked),
email addresses (ignoring `*@example.com/.org/.net`, `noreply` senders and an `--allow` file),
conservative phone forms (`+1 ...` and `(ddd) ddd-dddd`), public IPv4 addresses, and every
term of a denylist.

**The denylist is yours and is never committed.** It is where the real names go: people,
clients, internal code names, hostnames. Keep it as `.sensitive-denylist` at the repo root
(gitignored; picked up automatically) and, for CI, as the `SENSITIVE_DENYLIST` repository
secret, which `validate.yml` writes to a temporary file outside the checkout. This repository
ships no denylist because the file would itself be the leak. Tests that need a secret-shaped
string build it at runtime so the scan of the repository stays clean.

## Adapters (`scripts/adapters/`)

Each adapter is a class with `__init__(ctx)` and `fetch_page(slug, entry) -> FetchedPage`
(`base.py`). `canon_sync.ADAPTERS` maps `source_of_truth` values to classes.

**markdown** (`markdown.py`): `entry.id` is a path under `source_root`; the file's YAML
frontmatter is parsed, checked against the contract (`slug`, `status`, `owner`) and exported
verbatim. Works for Obsidian and any git vault. This is what the sample contract uses.

**notion** (`notion.py`): fetches by page ID through the REST API with `NOTION_TOKEN` from the
environment and `Notion-Version: 2025-09-03`. Needs a live workspace to exercise; the tests
cover only the block-to-markdown conversion and the HTTP retry logic with fakes. To adopt it:

1. Create an internal Notion integration, share every canonical page with it, and put the
   32-hex page IDs in `canonical_pages[*].id` (see `templates/contracts/context-contract.notion.yaml`).
2. Export `NOTION_TOKEN` locally (`.env`, never committed) and add it as a repository secret.
3. Run `canon_sync.py --dry-run` once and read the summary, then run it for real and read the
   exported markdown. Unsupported block types appear as `<!-- unsupported block: TYPE -->`;
   add a branch in `blocks_to_markdown` for the ones your pages use.
4. Frontmatter is synthesised from the contract entry (slug, owner, status, review,
   visibility) plus the contract-level review dates and the Notion title; the Notion page
   itself carries no YAML block.

**confluence** (`confluence.py`): a documented stub that raises `NotImplementedError` and
points at the two ways forward (export to markdown, or implement the class).

### Adding an adapter

1. Copy `markdown.py` to `scripts/adapters/<name>.py`. Keep the class shape and return a
   `FetchedPage`: set `available=False` with a note when a page cannot be read, add to
   `problems` when something is wrong enough to fail the sync (the sync fails on any problem),
   and fill `frontmatter`, `body`, `title`, `url` and `next_review` otherwise.
2. Register it in `canon_sync.ADAPTERS` and, if it is a new `source_of_truth` value, add the
   value to `common.SOURCE_OF_TRUTH_VALUES`, `docs/formats.md` and the JSON Schemas.
3. Read credentials from environment variables only and never print them.
4. Add an offline test with fake responses (see `tests/test_notion_adapter_offline.py`).

## CI

- `.github/workflows/validate.yml` runs on push and pull request: tests, contract validation,
  a sample sync (gates fail the job; warnings do not, so the template keeps passing after the
  sample pages' review dates; add `--fail-on-warn` in your fork), and the sensitive scan.
- `.github/workflows/canon-sync.yml` runs nightly and on demand: syncs the contract named by
  the `CONTEXT_CONTRACT` repository variable (default: the markdown sample) into `export/`,
  opens a pull request with `peter-evans/create-pull-request@v8` when `generated_at` moved,
  commits a heartbeat when only `last_synced_at` moved, and runs `check_freshness.py` even
  when the sync failed so a broken sync shows up as a failed job with the mirror's real age.
- `.github/PULL_REQUEST_TEMPLATE.md` asks the one review question that matters for a
  generated mirror: is this a sane export?
