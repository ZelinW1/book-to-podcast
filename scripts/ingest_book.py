#!/usr/bin/env python3
"""Extract a book into a compact index and bounded, traceable text chunks."""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import zipfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET


BLOCK_TAGS = {"p", "div", "section", "article", "li", "blockquote", "br", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}


class TextHTML(HTMLParser):
    def __init__(self, mark_headings: bool = False) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.headings: list[str] = []
        self.hidden = 0
        self.heading: list[str] | None = None
        self.mark_headings = mark_headings

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag in BLOCK_TAGS:
            self.parts.append("\n")
        if re.fullmatch(r"h[1-6]", tag):
            self.heading = []
            if self.mark_headings:
                self.parts.append("# ")
        if tag == "img":
            alt = dict(attrs).get("alt")
            if alt:
                self.parts.append(f" [图：{alt}] ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        if re.fullmatch(r"h[1-6]", tag) and self.heading is not None:
            title = " ".join("".join(self.heading).split())
            if title:
                self.headings.append(title)
            self.heading = None
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)
            if self.heading is not None:
                self.heading.append(data)

    def text(self) -> str:
        lines = [" ".join(line.split()) for line in "".join(self.parts).splitlines()]
        return "\n\n".join(line for line in lines if line)


def decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeError:
            pass
    return data.decode("utf-8", errors="replace")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def epub_path(base: str, href: str) -> str:
    path = unquote(urlsplit(href).path)
    return posixpath.normpath(posixpath.join(posixpath.dirname(base), path))


def epub_toc(archive: zipfile.ZipFile, opf_path: str, manifest: dict[str, dict[str, str]]) -> dict[str, str]:
    names = set(archive.namelist())
    titles: dict[str, str] = {}
    for item in manifest.values():
        if item.get("media-type") != "application/x-dtbncx+xml":
            continue
        path = epub_path(opf_path, item["href"])
        if path not in names:
            continue
        root = ET.fromstring(archive.read(path))
        for point in root.iter():
            if local_name(point.tag) != "navPoint":
                continue
            label = next((e for e in point.iter() if local_name(e.tag) == "text"), None)
            content = next((e for e in point.iter() if local_name(e.tag) == "content"), None)
            if label is not None and content is not None and content.get("src"):
                titles.setdefault(epub_path(path, content.get("src", "")), " ".join("".join(label.itertext()).split()))
    for item in manifest.values():
        if "nav" not in item.get("properties", "").split():
            continue
        path = epub_path(opf_path, item["href"])
        if path not in names:
            continue
        root = ET.fromstring(archive.read(path))
        for link in root.iter():
            if local_name(link.tag) == "a" and link.get("href"):
                label = " ".join("".join(link.itertext()).split())
                if label:
                    titles.setdefault(epub_path(path, link.get("href", "")), label)
    return titles


def read_epub(path: Path) -> tuple[dict, list[dict]]:
    with zipfile.ZipFile(path) as archive:
        container = ET.fromstring(archive.read("META-INF/container.xml"))
        rootfile = next(e for e in container.iter() if local_name(e.tag) == "rootfile")
        opf_path = rootfile.attrib["full-path"]
        opf = ET.fromstring(archive.read(opf_path))
        meta: dict[str, str] = {}
        for element in opf.iter():
            name = local_name(element.tag)
            if name in {"title", "creator", "language"} and element.text and name not in meta:
                meta[name] = " ".join(element.text.split())
        manifest = {e.attrib["id"]: e.attrib for e in opf.iter() if local_name(e.tag) == "item" and e.get("id")}
        toc = epub_toc(archive, opf_path, manifest)
        sections: list[dict] = []
        names = set(archive.namelist())
        for ref in opf.iter():
            if local_name(ref.tag) != "itemref" or ref.get("linear") == "no":
                continue
            item = manifest.get(ref.get("idref", ""))
            if not item or item.get("media-type") not in {"application/xhtml+xml", "text/html"}:
                continue
            member = epub_path(opf_path, item["href"])
            if member not in names:
                raise ValueError(f"EPUB spine member missing: {member}")
            parser = TextHTML()
            parser.feed(decode(archive.read(member)))
            body = parser.text()
            if body:
                title = toc.get(member) or (parser.headings[0] if parser.headings else "")
                if not title:
                    title = f"{re.sub(r'(（续）)+$', '', sections[-1]['title'])}（续）" if sections else member
                sections.append({"title": title, "locator": member, "text": body})
        if not sections:
            raise ValueError("EPUB has no readable spine text")
        leading = Counter(section["text"].split("\n\n", 1)[0] for section in sections)
        repeated, count = leading.most_common(1)[0]
        if len(repeated) <= 80 and count >= max(3, len(sections) * 0.6):
            for section in sections:
                if section["text"].startswith(repeated + "\n\n"):
                    section["text"] = section["text"][len(repeated) + 2 :]
            meta["removed_repeated_header"] = repeated
        return meta, sections


def read_pdf(path: Path, ocr: str, ocr_language: str) -> tuple[dict, list[dict]]:
    try:
        import pymupdf
    except ImportError as error:
        raise RuntimeError("PDF ingestion needs PyMuPDF: pip install pymupdf") from error
    sections: list[dict] = []
    with pymupdf.open(path) as doc:
        toc = sorted((page, title) for level, title, page in doc.get_toc() if level <= 2)
        meta = {key: value for key, value in doc.metadata.items() if key in {"title", "author"} and value}
        current_title = ""
        toc_index = 0
        for index, page in enumerate(doc):
            while toc_index < len(toc) and toc[toc_index][0] <= index + 1:
                current_title = toc[toc_index][1]
                toc_index += 1
            body = page.get_text("text", sort=True).strip()
            used_ocr = False
            if len(body) < 30 and ocr == "auto":
                textpage = page.get_textpage_ocr(language=ocr_language)
                body = page.get_text("text", textpage=textpage, sort=True).strip()
                used_ocr = True
            if body:
                sections.append({"title": current_title or f"Page {index + 1}", "locator": f"page:{index + 1}", "text": body, "ocr": used_ocr})
    if not sections:
        raise ValueError("PDF has no extracted text; try --ocr auto with the correct language pack")
    return meta, sections


def read_docx(path: Path) -> tuple[dict, list[dict]]:
    try:
        from docx import Document
    except ImportError as error:
        raise RuntimeError("DOCX ingestion needs python-docx: pip install python-docx") from error
    document = Document(path)
    sections: list[dict] = []
    title = path.stem
    body: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        if paragraph.style.name.lower().startswith("heading") and body:
            sections.append({"title": title, "locator": f"heading:{len(sections) + 1}", "text": "\n\n".join(body)})
            title, body = text, []
        elif paragraph.style.name.lower().startswith("heading"):
            title = text
        else:
            body.append(text)
    if body:
        sections.append({"title": title, "locator": f"heading:{len(sections) + 1}", "text": "\n\n".join(body)})
    return {"title": document.core_properties.title or path.stem}, sections


def read_plain(path: Path) -> tuple[dict, list[dict]]:
    raw = decode(path.read_bytes())
    if path.suffix.lower() in {".html", ".htm"}:
        parser = TextHTML(mark_headings=True)
        parser.feed(raw)
        raw = parser.text()
    parts = re.split(r"(?m)^(#{1,3}\s+.+)$", raw)
    sections: list[dict] = []
    if len(parts) == 1:
        sections.append({"title": path.stem, "locator": "text:1", "text": raw.strip()})
    else:
        if parts[0].strip():
            sections.append({"title": path.stem, "locator": "text:1", "text": parts[0].strip()})
        for number in range(1, len(parts), 2):
            body = parts[number + 1].strip()
            if body:
                sections.append({"title": parts[number].lstrip("# ").strip(), "locator": f"heading:{number // 2 + 1}", "text": body})
    return {"title": path.stem}, [section for section in sections if section["text"]]


def chunks_of(text: str, limit: int) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    result: list[str] = []
    current = ""
    for paragraph in paragraphs:
        while len(paragraph) > limit:
            cut = max(paragraph.rfind("。", 0, limit), paragraph.rfind(". ", 0, limit), paragraph.rfind("；", 0, limit))
            cut = cut + 1 if cut > limit // 2 else limit
            piece, paragraph = paragraph[:cut].strip(), paragraph[cut:].strip()
            if current:
                result.append(current)
                current = ""
            result.append(piece)
        if len(current) + len(paragraph) + 2 > limit and current:
            result.append(current)
            current = ""
        current = f"{current}\n\n{paragraph}" if current else paragraph
    if current:
        result.append(current)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chunk-chars", type=int, default=5000)
    parser.add_argument("--ocr", choices=["off", "auto"], default="off")
    parser.add_argument("--ocr-language", default="eng")
    args = parser.parse_args()
    if args.chunk_chars < 500:
        parser.error("--chunk-chars must be at least 500")
    book = args.book.resolve()
    if not book.is_file():
        parser.error(f"book not found: {book}")
    suffix = book.suffix.lower()
    if suffix == ".epub":
        meta, sections = read_epub(book)
    elif suffix == ".pdf":
        meta, sections = read_pdf(book, args.ocr, args.ocr_language)
    elif suffix == ".docx":
        meta, sections = read_docx(book)
    elif suffix in {".html", ".htm", ".txt", ".md", ".markdown"}:
        meta, sections = read_plain(book)
    else:
        parser.error(f"unsupported format: {suffix}")
    digest = hashlib.sha256(book.read_bytes()).hexdigest()
    output = args.output.resolve()
    manifest_path = output / "book.json"
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if old.get("sha256") != digest:
            parser.error("output already belongs to another book")
    chunk_dir = output / "chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    section_records: list[dict] = []
    for section_number, section in enumerate(sections, 1):
        chunk_ids: list[str] = []
        for piece in chunks_of(section["text"], args.chunk_chars):
            chunk_id = f"c{len(records) + 1:04d}"
            (chunk_dir / f"{chunk_id}.txt").write_text(piece + "\n", encoding="utf-8")
            records.append({"id": chunk_id, "section": section_number, "title": section["title"], "locator": section["locator"], "chars": len(piece), "sha256": hashlib.sha256(piece.encode()).hexdigest()})
            chunk_ids.append(chunk_id)
        section_records.append({"order": section_number, "title": section["title"], "locator": section["locator"], "chars": len(section["text"]), "chunks": chunk_ids, "ocr": section.get("ocr", False)})
    manifest = {"schema": 1, "source": str(book), "sha256": digest, "format": suffix.lstrip("."), "metadata": meta, "sections": section_records, "chunks": records}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [f"# {meta.get('title') or book.stem}", "", f"Source format: {suffix.lstrip('.')} | Sections: {len(sections)} | Chunks: {len(records)}", "", "Read only the chunk files needed for the current episode.", ""]
    for section in section_records:
        note = " [OCR]" if section["ocr"] else ""
        lines.append(f"- {section['order']:03d} {section['title']} ({section['chars']} chars; {section['locator']}){note}: {', '.join(section['chunks'])}")
    (output / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"title": meta.get("title") or book.stem, "sections": len(sections), "chunks": len(records), "index": str(output / "index.md")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
