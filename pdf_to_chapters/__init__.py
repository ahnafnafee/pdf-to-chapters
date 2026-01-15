"""
PDF to Chapters - Split PDFs into chapters based on bookmarks using AI inference.
"""

from pdf_to_chapters.pdf_utils import extract_bookmarks, split_pdf_by_chapters
from pdf_to_chapters.ai_utils import get_primary_chapters_from_ai, parse_toc_with_ai
from pdf_to_chapters.toc_utils import extract_toc_text, calculate_page_offset
from pdf_to_chapters.utils import sanitize_filename, format_bookmarks_for_ai

__version__ = "0.1.0"
__all__ = [
    "extract_bookmarks",
    "split_pdf_by_chapters",
    "get_primary_chapters_from_ai",
    "parse_toc_with_ai",
    "extract_toc_text",
    "calculate_page_offset",
    "sanitize_filename",
    "format_bookmarks_for_ai",
]
