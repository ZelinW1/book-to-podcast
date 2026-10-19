"""Small behavior tests for source order, bounded chunks, and spoken text."""

import sys
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ingest_book import chunks_of, read_epub
from tts_qwen import read_script, split_speech

try:
    from render_video import parse_subtitles
except ModuleNotFoundError as error:
    if error.name != "PIL":
        raise
    parse_subtitles = None


class IngestTests(unittest.TestCase):
    def test_epub_uses_spine_not_archive_order(self):
        book = BytesIO()
        with zipfile.ZipFile(book, "w") as archive:
            archive.writestr("META-INF/container.xml", '<container><rootfiles><rootfile full-path="OPS/content.opf"/></rootfiles></container>')
            archive.writestr("OPS/content.opf", '''<package xmlns="http://www.idpf.org/2007/opf"><metadata><title xmlns="http://purl.org/dc/elements/1.1/">Test</title></metadata><manifest><item id="a" href="a.xhtml" media-type="application/xhtml+xml"/><item id="b" href="b.xhtml" media-type="application/xhtml+xml"/><item id="x" href="x.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="b"/><itemref idref="x" linear="no"/><itemref idref="a"/></spine></package>''')
            archive.writestr("OPS/a.xhtml", "<html><body><h1>First</h1><p>A text.</p></body></html>")
            archive.writestr("OPS/b.xhtml", "<html><body><h1>Second</h1><p>B text.</p></body></html>")
            archive.writestr("OPS/x.xhtml", "<html><body><p>Excluded.</p></body></html>")
        book.seek(0)
        metadata, sections = read_epub(book)
        self.assertEqual(metadata["title"], "Test")
        self.assertEqual([section["title"] for section in sections], ["Second", "First"])
        self.assertNotIn("Excluded", " ".join(section["text"] for section in sections))

    def test_chunking_keeps_text_bounded_and_in_order(self):
        text = "甲。" * 230 + "\n\n" + "乙。" * 230
        chunks = chunks_of(text, 500)
        self.assertTrue(all(len(chunk) <= 500 for chunk in chunks))
        self.assertEqual("".join(chunks).replace("\n", ""), text.replace("\n", ""))


class ScriptTests(unittest.TestCase):
    def test_source_comments_are_not_spoken(self):
        script = Mock()
        script.read_text.return_value = "# Title\n<!-- language: Chinese -->\n## 旁白\n<!-- source: c0001,c0002 -->\n这是第一句。第二句。\n"
        title, language, turns = read_script(script)
        self.assertEqual((title, language), ("Title", "Chinese"))
        self.assertEqual(turns[0]["source"], ["c0001", "c0002"])
        self.assertEqual("".join(split_speech(turns[0]["text"], 20)).replace(" ", ""), turns[0]["text"].replace(" ", ""))


@unittest.skipIf(parse_subtitles is None, "Pillow is optional for video rendering")
class SubtitleTests(unittest.TestCase):
    def test_aligned_srt_has_independent_cues(self):
        path = Mock(spec=Path)
        path.read_text.return_value = "1\n00:00:01,000 --> 00:00:02,500\n第一句\n\n2\n00:00:03,000 --> 00:00:04,000\n第二句\n"
        self.assertEqual(parse_subtitles(path), [
            {"start": 1.0, "end": 2.5, "text": "第一句"},
            {"start": 3.0, "end": 4.0, "text": "第二句"},
        ])

    def test_overlapping_cues_are_rejected(self):
        path = Mock(spec=Path)
        path.read_text.return_value = "1\n00:00:01,000 --> 00:00:03,000\n第一句\n\n2\n00:00:02,000 --> 00:00:04,000\n第二句\n"
        with self.assertRaises(ValueError):
            parse_subtitles(path)


if __name__ == "__main__":
    unittest.main()
