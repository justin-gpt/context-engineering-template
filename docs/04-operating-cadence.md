# Operating cadence

Attach context review to rhythms that already exist. The project status meeting updates project health and decisions; a monthly delivery review triages gaps and deployment issues; a quarterly review re-verifies durable context and access. Standalone maintenance tasks age unnoticed.

| Cadence | Review |
| --- | --- |
| Every agent run | Confirm tenant and deployment; load the manifest; record source versions; enforce write authority; capture result and exceptions; append a heartbeat |
| Weekly | Update project health, completed work, next work, blockers, decisions needed, milestones, deliverables, capacity, and the client portal |
| Monthly | Triage context gaps; review active deployments and failures; reconcile hours and value; rotate integrations due; retire duplicate or stale records |
| Quarterly | Re-verify canon; review permissions and guest access; evaluate agent releases; confirm portfolio priorities; review retention, reuse and cross-client learning |
| On change | Impact assessment, tests, approval, canary, release, documentation, rollback readiness |
| On project close | Accept deliverables, complete handoff, freeze final status, archive work, revoke unnecessary access, start retention |
| On client close | Export or transfer agreed materials; disable agents, schedules, webhooks, integrations, guests and credentials; preserve only authorized anonymized learning |

## The three commands you run most

```bash
python scripts/canon_sync.py --contract <contract> --out export/        # nightly in CI; by hand after a big edit
python scripts/check_freshness.py export/meta.json --contract <contract>   # daily; exit 2 pages the sync owner
python scripts/scan_sensitive.py . --denylist /path/outside/the/repo/.sensitive-denylist   # before every push of shared material
```

## Owner rituals

- **Page owners** (roles): re-verify on cadence, resolve `[CONFIRM]` and `[YOU DECIDE]` markers, flip status in the contract, append a change-log line. Twenty minutes a month per page is the budget; if it is not on the calendar it will not happen.
- **Agent operator:** watch the heartbeat; triage new gap rows within two weeks and send a monthly digest to owners; keep the gap tracker's options equal to the contract's slugs; review deployment scopes and last-access dates quarterly.
- **Curators:** run the write-side skills (populate, migrate, drift check) and hand drafts to owners; never ground a page themselves.

## Lessons the cadence exists to prevent

Freshness drift is silent; ratification is the bottleneck; the gap backlog ages; Layer 3 ownership lags grounding; human and machine trust signals diverge; isolation creates dead links; duplicate surfaces fork truth; adoption is an operating problem. Each has a line in the tables above. The full observations are in `01-business-pattern.md` § What running it taught.

Pilot gates, the permission test, the publishing checklist, the offboarding sequence and the release lifecycle are in `skills/context-engineering-setup/references/checklists.md` so the setup skill and the humans read the same list.
