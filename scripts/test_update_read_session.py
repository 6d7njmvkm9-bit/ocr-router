#!/usr/bin/env python3
"""Tests for update-read-session.py merge logic."""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "update-read-session.py"

def _hash(s): return hashlib.sha256(s.encode()).hexdigest()
def _make_item(**kw):
    base = {"schema_version":"read-item/1.0","file":"test.pdf","file_hash":_hash("test"),"type":"scanned_pdf","page_count":10,"processed_pages":[1,2,3],"unprocessed_pages":[],"read_status":"read","reader_used":"paddleocr","extracted_text_ref":"/tmp/r.md","raw_text_ref":None,"archive_ref":None,"postprocess_applied":False,"postprocess_log_ref":None,"needs_visual_review":[],"warnings":[],"api_error":None,"cache_key":None}
    base.update(kw)
    return base

def main():
    with tempfile.TemporaryDirectory() as tmp:
        wd = Path(tmp) / "case"
        md = wd / ".material-reading"
        md.mkdir(parents=True)
        i1 = md / "_read_item_1.json"
        i1.write_text(json.dumps(_make_item(file="a.pdf"), ensure_ascii=False))
        rc = subprocess.run([sys.executable, str(SCRIPT), "--work-dir", str(wd), "--read-item", str(i1)], capture_output=True, text=True).returncode
        assert rc == 0, f"rc={rc}"
        assert (md / "read-session.json").is_file()
        print("ALL TESTS PASSED")

if __name__ == "__main__":
    main()
