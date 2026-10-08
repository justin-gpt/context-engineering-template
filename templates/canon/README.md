# Sample canon (markdown vault)

Nine canonical pages for **Acme Analytics**, a fictional mid-market B2B SaaS company. This folder is both:

- the **sample content** for a company canon (what each page answers, how thin it stays, how it points to depth), and
- a working **markdown source** for the sync: `templates/contracts/context-contract.yaml` points at these files, so `python scripts/canon_sync.py --contract templates/contracts/context-contract.yaml --out export/` exports them exactly as a Notion canon would be exported.

If you keep your canon in Obsidian or any git vault, copy this folder, keep the frontmatter, and edit the prose. If you keep it in Notion, create one page per file (see `docs/06-notion-templates.md`) and put the frontmatter fields in the metadata callout at the top of each page.

| Slug | Answers | Owner role | Status in the sample |
| --- | --- | --- | --- |
| `company_readme` | Who we are, how we operate, roles, systems of record, terminology | CEO | grounded |
| `positioning` | Category, who it is for, what makes it different, what it is not | CEO + PMM | grounded |
| `messaging` | Value proposition, pillars, value by persona, boilerplate, claims not made | PMM | grounded |
| `sales_storyboard` | The validated narrative reps tell, objections, approved responses | PMM / Sales Enablement | draft |
| `icp_personas` | Who buys, who champions, triggers, disqualifiers, objections | PMM | grounded |
| `competitive_battlecards` | Thin summary over a depth database of cards; refresh rules | PMM / Competitive Intel | draft |
| `glossary` | Canonical terms with per-term GROUNDED / GENERIC tags; no formulas | Product + Data | draft |
| `brand_voice` | How the company and its agents sound | PMM / Brand | grounded |
| `operating_rules` | The one page allowed to direct an agent: read order, write paths, precedence | agent_operator | grounded |

Three pages are deliberately left in draft with open `[CONFIRM]` and `[YOU DECIDE]` markers, because that is what a real canon looks like two months in: authoring is fast, owner verification is the bottleneck. The sync refuses to mark a page `grounded` while a marker remains.

Rules the whole folder follows: owners are roles, not people; every page ends with a dated change log; metric values never appear (definitions live in `templates/databases/metrics-catalog.csv`, values are pulled live); depth is linked, never copied.
