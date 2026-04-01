"""Tests for inventory tracking and checksum behavior."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inventory import Inventory


class TestInventory(unittest.TestCase):
    def test_add_includes_sha256_for_regular_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "data.json"
            file_path.write_text('{"k":"v"}', encoding="utf-8")

            inv = Inventory()
            inv.add("test", "sample", str(file_path))

            self.assertIn("sha256", inv.entries[0])
            self.assertNotIn("hash_error", inv.entries[0])

    @patch("inventory.writers.file_hash", side_effect=OSError("unreadable"))
    def test_add_records_hash_error_when_hashing_fails(self, _mock_hash):
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "data.json"
            file_path.write_text("{}", encoding="utf-8")

            inv = Inventory()
            inv.add("test", "sample", str(file_path))

            self.assertNotIn("sha256", inv.entries[0])
            self.assertEqual(inv.entries[0]["hash_error"], "unreadable")


if __name__ == "__main__":
    unittest.main()
