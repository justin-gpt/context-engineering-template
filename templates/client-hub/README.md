# Client hub templates (consultancy pattern)

The thin client canon that lives inside each client's delivery hub: four pages, each with an owner role, a status, a client-visibility flag, an agent-readable flag and a review date. The client context contract (`templates/contracts/client-context-contract.yaml`) names them; a project manifest narrows them to what one deployment needs.

| Page | Answers | Owner role | Default visibility |
| --- | --- | --- | --- |
| `client_readme.md` | Who the client is, how the engagement operates, key roles, terminology, where the authoritative systems live | engagement_lead | client_shared |
| `engagement_scope.md` | Objectives, deliverables, boundaries, success measures, decision rights, cadence | engagement_lead | client_shared |
| `operating_rules.md` | Approved client procedures that may instruct an agent, with version and effective date | client_process_owner | client_private |
| `glossary_metrics.md` | Canonical terms and how each metric is defined and pulled live, without values | client_data_owner | client_private |

Start with these four; add `positioning_voice.md`, `product_service_map.md`, `stakeholders_decision_rights.md` and `integration_data_map.md` when the engagement touches them (the reference architecture's full set is six to ten). Canon stays thin and points to the hub's databases (Work Items, Status Updates, Decisions, Risks) and to source artifacts.

Placeholders are in angle brackets. Roles, not names. Commercial terms live in the Engagements database, never on a page. The sample filled-in versions use the fictional client Globex Logistics and are linked from `docs/06-notion-templates.md`.
