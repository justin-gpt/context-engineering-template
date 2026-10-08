# Contributing

Thank you for improving the template. Three rules, then the mechanics.

## Rules

1. **Fictional data only.** No real company, client, customer, person, email, phone, address, ID, URL or credential, anywhere, including commit messages and test fixtures. Use Acme Analytics, Globex Logistics, Vandelay Industries, roles instead of names, `example.com`, and angle-bracket placeholders. `python scripts/scan_sensitive.py .` must pass; maintainers also run it with a private denylist.
2. **Keep the formats in step.** If you change a file shape, change `docs/formats.md`, the JSON Schema in `schemas/json/`, the script that reads or writes it, and its test, in the same pull request.
3. **Platform-neutral by default.** New material should work for a markdown vault and for Notion unless it is explicitly an adapter or a platform playbook, in which case it lives in `scripts/adapters/`, `schemas/vector/` or the setup skill's references.

## Mechanics

```bash
pip install -r requirements.txt
python -m pytest -q
python scripts/validate_contract.py templates/contracts/*.yaml
python scripts/canon_sync.py --contract templates/contracts/context-contract.yaml --out /tmp/export
python scripts/scan_sensitive.py .
claude plugin validate .        # if you touched the marketplace or a plugin
```

Open a pull request with a short description of what changed and why. For a new adapter, include an offline test with fake responses (see `tests/test_notion_adapter_offline.py`). For a new vector-store schema, include the metadata contract fields and a filtered query example. For a new skill, keep the `SKILL.md` frontmatter (`name`, `description`) and put long material in `references/`.

## What we will not merge

Anything that stores a secret in a page, contract or manifest; anything that makes an agent edit canon directly; anything that relies on a view filter for tenant isolation; anything with real data.
