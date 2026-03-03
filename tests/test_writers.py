"""Tests for writers."""

import json
import tempfile
import unittest
from pathlib import Path

from ado_backup.writers import append_jsonl, write_binary, write_json


class TestWriteJson(unittest.TestCase):
    def test_write_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub" / "test.json"
            data = {"key": "value", "num": 42}
            write_json(path, data)
            self.assertTrue(path.exists())
            loaded = json.loads(path.read_text())
            self.assertEqual(loaded["key"], "value")
            self.assertEqual(loaded["num"], 42)

    def test_pretty_printed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.json"
            write_json(path, {"a": 1})
            content = path.read_text()
            self.assertIn("\n", content)  # pretty-printed

    def test_sorted_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.json"
            write_json(path, {"z": 1, "a": 2, "m": 3})
            content = path.read_text()
            keys = list(json.loads(content).keys())
            self.assertEqual(keys, ["a", "m", "z"])


class TestWriteBinary(unittest.TestCase):
    def test_write_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.bin"
            data = b"\x00\x01\x02\x03"
            write_binary(path, data)
            self.assertEqual(path.read_bytes(), data)


class TestAppendJsonl(unittest.TestCase):
    def test_append_multiple(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.jsonl"
            append_jsonl(path, {"id": 1})
            append_jsonl(path, {"id": 2})
            lines = path.read_text().strip().split("\n")
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["id"], 1)
            self.assertEqual(json.loads(lines[1])["id"], 2)


if __name__ == "__main__":
    unittest.main()
