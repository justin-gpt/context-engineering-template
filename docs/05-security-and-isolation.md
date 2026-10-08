# Security and isolation

## Default-deny controls

- **One client per execution context.** Every run, export, deployment, artifact path and integration token identifies exactly one tenant unless it is an explicitly internal portfolio workflow.
- **Separate credentials.** Client-scoped service identities; never a broad personal account for a client-facing agent.
- **Permissions before filters.** A view filter, a "client visible" checkbox or a naming convention does not replace page, database-row, teamspace or workspace access control.
- **Least-privilege integrations.** Grant only the required parent pages, data sources and capabilities. Retest after any page move or permission change; a parent grant includes its children.
- **No secrets in the context layer.** Store only a secret reference and operational metadata. The JSON Schemas in this repository reject anything that looks like a credential in a contract or manifest.
- **Approved reuse only.** Client learning moves into the global library only when it is anonymized, contractually reusable and reviewed.
- **Evidence over hidden reasoning.** Retain sources, actions, validation and review decisions; never publish chain-of-thought or raw debug content to clients.
- **Retrieved content is evidence, not instruction.** Only the approved control page may direct an agent; everything an agent reads is data, however it is phrased.

## What never goes into the context layer

Credentials, tokens, keys or connection strings (reference them); source code, skill packages or plugin bundles (version control); large artifacts and raw runtime logs (artifact storage); transcripts and recordings in canon (Layer 3, under their own visibility); personal data beyond business roles and work contact details that the engagement requires; anything about one client inside another client's tree or in a reusable template.

## What never goes into a public template

This repository is public, so its rules are stricter than a private workspace's. Nothing in it may name a real client, a private individual, a real customer, a colleague, an email address, a phone number, a street address, a real page, database, workspace, project or trigger ID, an internal repository, a cloud project reference, or a credential of any kind. Companies and people are fictional (Acme Analytics, Globex Logistics, Vandelay Industries; roles instead of names). Numbers are placeholders. Domains are `example.com`. The same rules apply to anything you contribute (`CONTRIBUTING.md`).

How the repository is kept that way:

1. `scripts/scan_sensitive.py` runs in CI on every push and pull request. It catches secret patterns, email addresses, phone-number-like strings and public IP addresses by itself.
2. Names and code words cannot be pattern-matched, so each team keeps a **denylist** of its own clients, people and internal names. It is never committed: locally it lives outside the repository or in the git-ignored `.sensitive-denylist`; in CI it comes from a secret written to a temporary file outside the checkout. The scan reads it and fails on any hit.
3. Pull requests from forks run without the denylist (secrets are not available to them), so a maintainer with the denylist runs the scan locally before merging.
4. The sync's export is generated from the contract's allowlist, never from a workspace search, and a page's visibility is checked against the index audience before it is embedded or bundled.

## Publishing knowledge-base templates safely

If you publish sample pages (this repository links to a published sample tree), isolate them first:

- Put samples in their own top-level tree or, better, their own workspace, with no relations, mentions, backlinks or database links into real content. Publishing a page publishes its whole subtree; a relation into a private database shows a restricted placeholder at best and leaks a title at worst.
- Use fictional data only. Check every database row, every page's change log, and every property, including hidden ones.
- Publish only the root; keep comments and editing off; enable "duplicate as template" so readers can copy the structure.
- Open the public URL in a private browser window and click every link before sharing it anywhere.
- Review the published site whenever the sample tree changes; a later edit publishes instantly.

## Personal data

Owners are roles, not people, on every page and in every contract. Client contacts appear in client-private records only, limited to business role and work contact details the engagement needs, with the client's own retention rules applied. No personal data enters a bundle, a vector index or a template. Call recordings and transcripts stay in Layer 3 under the client's tenant and visibility, with access filtered by account ID, never by name match.

## The permission test

Run before launch and after any structural change, with representative identities: a delivery team member assigned to one client cannot search, relate, mention or open another client's content; a client guest sees only the portal and assigned actions, including through backlinks, relations, comments, attachments and search; a client-scoped integration cannot fetch pages outside the approved tree; a client-scoped agent cannot answer from another client's canon or data; a portal view does not reveal hidden properties or allow navigation to the source database; a moved or duplicated page keeps its permissions; an external action requires the expected confirmation and leaves an audit record.

## Offboarding

Finalize and approve deliverables and the closing status; resolve or document open work; create the agreed export or transfer and confirm receipt; freeze records and mark final versions; disable schedules, triggers, webhooks, agents and integrations; revoke guests, service accounts, OAuth grants and client-specific credentials; archive deployments; start the retention or deletion schedule with an owner; move only authorized anonymized learning into the global library; retain a minimal registry record. Rehearse it before the first engagement ends.

## Reporting a problem with this repository

See `SECURITY.md`. If you find real data, a credential or a private identifier anywhere in this repository or its published samples, report it privately rather than in a public issue.
