# Security policy

## What this repository must never contain

This repository is public and its contents are meant to be copied. It must never contain:

- credentials of any kind: API keys, tokens, passwords, connection strings, private keys, webhook URLs with embedded secrets;
- real client, customer or partner names, or anything that identifies an engagement;
- personal data: names of private individuals, email addresses, phone numbers, street addresses, calendar or meeting details;
- real identifiers: knowledge-base page, database, workspace or integration IDs, scheduled-task or trigger IDs, cloud project references, internal repository names, internal hostnames or IP addresses;
- transcripts, recordings, screenshots or exports of real systems.

Companies and people in the samples are fictional (Acme Analytics, Globex Logistics, Vandelay Industries; roles instead of names). Domains are `example.com`. IDs are placeholders in angle brackets.

## How it is enforced

- `scripts/scan_sensitive.py` runs in CI on every push and pull request (secret patterns, email addresses, phone-number-like strings, public IP addresses).
- Maintainers additionally run it with a private denylist of real names that is never committed (`docs/05-security-and-isolation.md`).
- Contributions are reviewed for fictional-data compliance before merge (`CONTRIBUTING.md`).

## Reporting

If you find real data, a credential or a private identifier in this repository, its history, or the published sample pages it links to, do not open a public issue. Use GitHub's private vulnerability reporting on this repository ("Report a vulnerability" under the Security tab), or contact the maintainers through the website linked in the README. Expect an acknowledgement within three business days. We will remove the content, rotate any credential, and rewrite history where needed.

## Scope notes for adopters

The scripts here read your knowledge base with a token you supply through the environment or your CI's secret store. They never print it, and the Notion adapter sends it only to the Notion API host. Review `scripts/adapters/` before granting an integration access, grant it the canon root only, and keep the mirror repository private unless your canon itself is public.
