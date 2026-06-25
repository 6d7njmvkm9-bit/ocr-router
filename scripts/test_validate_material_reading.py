#!/usr/bin/env python3
"""Regression tests for validate-material-reading.py."""
from __future__ import annotations
import hashlib, json, subprocess, sys, tempfile, unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("validate-material-reading.py")

class MaterialReadingGateTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.case_dir = Path(self.tempdir.name)
        self.raw_dir = self.case_dir / "raw"
        self.state_dir = self.case_dir / ".material-reading"
        self.raw_dir.mkdir()
        self.state_dir.mkdir()
        self.source = self.raw_dir / "evidence.txt"
        self.source.write_text("evidence")
        self.extracted = self.state_dir / "evidence.txt"
        self.extracted.write_text("evidence")

    def tearDown(self):
        self.tempdir.cleanup()

    def write_inventory(self, status="read", material_type="text"):
        data = {"schema_version":"1.0","source_roots":["raw"],"material_inventory":[{"file":"raw/evidence.txt","file_hash":hashlib.sha256(self.source.read_bytes()).hexdigest(),"type":material_type,"page_count":1,"read_status":status,"processed_pages":[1],"unprocessed_pages":[],"visual_review_required_pages":[],"visual_review_completed_pages":[],"critical_unverified_pages":[],"reader_used":"direct_text","summary":"test","extracted_text_ref":".material-reading/evidence.txt"}],"unreadable_items":[],"needs_followup_review":[],"api_failures":[]}
        (self.state_dir/"material-inventory.json").write_text(json.dumps(data,ensure_ascii=False))

    def test_full_pass(self):
        self.write_inventory()
        rc = subprocess.run([sys.executable,str(SCRIPT),"--case-dir",str(self.case_dir),"--require-scope","strategy"],capture_output=True,text=True).returncode
        self.assertEqual(rc,0)

if __name__ == "__main__":
    unittest.main()
