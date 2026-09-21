"""Split Markdown / Obsidian notes into heading-scoped chunks for search."""

import hashlib
import re
from pathlib import PurePosixPath

from pydantic import BaseModel

_FRONT_MATTER = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.S)
_WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]")
_HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*#*\s*$")


class Chunk(BaseModel):
    id: str
    source: str  # path inside the vault, forward slashes
    heading: str  # "Parent > Child"
    text: str


def _clean(text: str) -> str:
    return _WIKILINK.sub(lambda m: (m.group(2) or m.group(1)).strip(), text)


def _split(text: str, max_chars: int) -> list[str]:
    parts: list[str] = []
    current = ""
    for paragraph in (p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()):
        while len(paragraph) > max_chars:  # a single paragraph longer than the limit
            cut = paragraph.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            if current:
                parts.append(current)
                current = ""
            parts.append(paragraph[:cut].strip())
            paragraph = paragraph[cut:].strip()
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
        else:
            parts.append(current)
            current = paragraph
    if current:
        parts.append(current)
    return parts


def chunk_markdown(text: str, source: str, max_chars: int = 1200) -> list[Chunk]:
    body = _clean(_FRONT_MATTER.sub("", text, count=1))
    default_heading = PurePosixPath(source).stem
    stack: list[tuple[int, str]] = []
    sections: list[tuple[str, list[str]]] = [(default_heading, [])]

    for line in body.splitlines():
        match = _HEADING.match(line)
        if match:
            level, title = len(match.group(1)), match.group(2).strip()
            stack = [(lvl, t) for lvl, t in stack if lvl < level] + [(level, title)]
            sections.append((" > ".join(t for _, t in stack), []))
        else:
            sections[-1][1].append(line)

    chunks: list[Chunk] = []
    for heading, lines in sections:
        for index, part in enumerate(_split("\n".join(lines), max_chars)):
            digest = hashlib.sha1(f"{source}\x00{heading}\x00{index}".encode()).hexdigest()[:16]
            chunks.append(Chunk(id=digest, source=source, heading=heading, text=part))
    return chunks
