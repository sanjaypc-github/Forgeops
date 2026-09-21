from forgeops.knowledge.chunking import chunk_markdown

DOC = """---
tags: [runbook]
---
# Checkout API
Intro text about [[Payments Service|payments]].

## Database pool
If requests time out, check the pool size. See [[DB Tuning]].

## Deploys
Rollback with the previous build.
"""


def test_splits_by_heading_and_cleans_obsidian_syntax():
    chunks = chunk_markdown(DOC, "Runbooks/checkout.md")
    headings = [c.heading for c in chunks]
    assert headings == ["Checkout API", "Checkout API > Database pool", "Checkout API > Deploys"]
    assert "payments" in chunks[0].text and "[[" not in chunks[0].text
    assert "DB Tuning" in chunks[1].text
    assert "tags:" not in " ".join(c.text for c in chunks)
    assert len({c.id for c in chunks}) == 3


def test_long_sections_are_split_under_max_chars():
    body = "# Big\n" + "\n\n".join(f"Paragraph {i} " + "word " * 60 for i in range(10))
    chunks = chunk_markdown(body, "big.md", max_chars=500)
    assert len(chunks) > 1 and all(len(c.text) <= 500 for c in chunks)


def test_text_before_any_heading_uses_the_file_name():
    chunks = chunk_markdown("Just a note without headings.", "Notes/quick.md")
    assert [c.heading for c in chunks] == ["quick"]
