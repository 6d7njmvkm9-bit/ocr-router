#!/usr/bin/env python3
"""PDF manipulation tools: page count, splitting, rendering."""
import pypdfium2

def get_page_count(filepath):
    pdf = pypdfium2.PdfDocument(filepath)
    return len(pdf)
