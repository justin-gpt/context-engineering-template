# Sample plugin marketplace

A marketplace is a directory with a `.claude-plugin/marketplace.json` that lists plugins and where to fetch them. This repository's marketplace file lives at the repository root, so the whole repository registers as one marketplace:

```bash
claude plugin marketplace add justin-gpt/context-engineering-template
claude plugin install company-context@context-engineering
```

Inside a session: `/plugin marketplace add justin-gpt/context-engineering-template`, then `/plugin install company-context@context-engineering`. Validate after any edit with `claude plugin validate .` from the repository root.

Four plugins, split the way the reference implementation learned to split them after two months: everyone installs the read side; a few curators also install the write side; consultancies add the client side; the setup skill is for whoever stands the system up.

| Plugin | Who installs it | Skills | Writes |
| --- | --- | --- | --- |
| `context-engineering-setup` | The person setting the system up | `context-engineering-setup` | Creates pages, databases and repositories only with the user's approval |
| `company-context` | Everyone who drafts company-voiced work | `company-context`, `report-gap` | One row in the gap tracker, after a dedup check |
| `context-curator` | A handful of curators | `populate-canon-page`, `migrate-legacy-wiki`, `session-drift-check` | Draft pages marked draft; proposals; never grounds anything |
| `client-context` | Delivery teams at a consultancy | `client-context`, `client-status-draft`, `publish-to-portal` | Rows marked Agent (draft); state transitions only after the checklist passes |

## Why the split

Bundling read and write skills shipped five write-path skills to everyone who installed the plugin to get positioning into a draft, including a research-filing skill whose trigger fired at the end of any research task. The read side is read-only, which is the whole point of making Layer 2 programmatic: every drafting session can load it. The write side is for heavy, owner-gated work. `context-curator` depends on `company-context`, so curators install both; everyone else installs one.

## How the bundle reaches a plugin

The nightly sync (`scripts/canon_sync.py`) writes `export/` in the mirror repository. In the reference implementation the same export was also copied into `marketplace/plugins/company-context/references/canon/`, so merging a sync pull request bumped the plugin's patch version and auto-updating plugins delivered the fresh bundle to every consumer. Do the same here: have the sync job copy `export/` into that folder and bump `version` in `plugin.json`, or point the skill at the mirror repository's raw files. Pages the sync cannot read arrive as explicit placeholders so no agent mistakes one for canon.

## Portability

Skills are plain `SKILL.md` files with YAML frontmatter (the Agent Skills format). A runtime that does not load plugins can still use them: paste the SKILL.md body into the agent's instructions and attach `export/bundle.json` as knowledge. Nothing in these plugins is specific to one model vendor beyond the install mechanism.

## Adding your own

Copy a plugin folder, change `name` in both `plugin.json` and the marketplace entry (they must match), write the skill, run `claude plugin validate .`. Keep client names, credentials and internal URLs out of anything in this folder: a plugin is reusable by definition, and reusable means it may travel to another tenant.
