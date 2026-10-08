"""Source adapters for canon_sync.py.

An adapter turns one canonical page in a knowledge base into a FetchedPage
(see base.py). canon_sync.py picks the adapter from the contract's
`source_of_truth` value:

    markdown   -> markdown.py   (a git vault, Obsidian, any folder of .md files)
    notion     -> notion.py     (Notion REST API; needs NOTION_TOKEN)
    confluence -> confluence.py (documented stub; raises NotImplementedError)

To add a source, copy markdown.py, implement `fetch_page`, and register the
class in canon_sync.ADAPTERS. See scripts/README.md, "Adding an adapter".
"""
