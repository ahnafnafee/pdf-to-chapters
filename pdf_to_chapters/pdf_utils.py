"""PDF extraction and manipulation utilities."""

import re
from pathlib import Path

import fitz  # PyMuPDF

from pdf_to_chapters.utils import sanitize_filename


def extract_bookmarks(pdf_path: str) -> list[dict]:
    """Extract all bookmarks from a PDF file with their page numbers and levels."""
    doc = fitz.open(pdf_path)
    toc = doc.get_toc(simple=False)
    
    bookmarks = []
    for item in toc:
        level, title, page_num = item[0], item[1], item[2]
        bookmarks.append({
            "level": level,
            "title": title.strip(),
            "page": page_num
        })
    
    doc.close()
    return bookmarks


def get_total_pages(pdf_path: str) -> int:
    """Get the total number of pages in a PDF."""
    doc = fitz.open(pdf_path)
    total = doc.page_count
    doc.close()
    return total


def get_chapter_page_ranges(bookmarks: list[dict], chapter_titles: list[str], total_pages: int) -> list[dict]:
    """Get page ranges for each identified chapter."""
    # Create a mapping of title to bookmark info
    title_to_bookmark = {}
    for bm in bookmarks:
        if bm["title"] not in title_to_bookmark:
            title_to_bookmark[bm["title"]] = bm
    
    chapter_ranges = []
    for i, title in enumerate(chapter_titles):
        if title not in title_to_bookmark:
            print(f"Warning: Chapter '{title}' not found in bookmarks")
            continue
        
        bm = title_to_bookmark[title]
        start_page = bm["page"]
        
        # Find end page (next chapter's start - 1, or total_pages)
        end_page = total_pages
        
        # Look for next major section start
        for next_title in chapter_titles[i + 1:]:
            if next_title in title_to_bookmark:
                end_page = title_to_bookmark[next_title]["page"] - 1
                break
        
        if start_page > 0 and start_page <= end_page:
            chapter_ranges.append({
                "title": title,
                "start_page": start_page,
                "end_page": end_page
            })
    
    return chapter_ranges


def split_pdf_by_chapters(pdf_path: str, chapter_ranges: list[dict], output_dir: Path) -> list[str]:
    """Split PDF into separate files for each chapter."""
    doc = fitz.open(pdf_path)
    output_files = []
    
    for i, chapter in enumerate(chapter_ranges, 1):
        # Create sanitized filename
        safe_title = sanitize_filename(chapter["title"])
        output_filename = f"{i:02d}_{safe_title}.pdf"
        output_path = output_dir / output_filename
        
        # Create new PDF with chapter pages (PyMuPDF uses 0-indexed pages)
        start_idx = chapter["start_page"] - 1
        end_idx = chapter["end_page"] - 1
        
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=start_idx, to_page=end_idx)
        new_doc.save(str(output_path))
        new_doc.close()
        
        output_files.append(str(output_path))
        print(f"  Created: {output_filename} (pages {chapter['start_page']}-{chapter['end_page']})")
    
    doc.close()
    return output_files


def add_bookmarks_to_pdf(pdf_path: str, chapter_ranges: list[dict], output_path: str) -> str:
    """
    Add chapter bookmarks to a PDF file and save to output_path.
    
    Args:
        pdf_path: Path to the source PDF
        chapter_ranges: List of dicts with 'title' and 'start_page' keys
        output_path: Where to save the bookmarked PDF
    
    Returns:
        The output path
    """
    doc = fitz.open(pdf_path)
    
    # Build TOC structure for PyMuPDF
    # Format: [level, title, page_number, ...]
    # Level 1 = top-level bookmark
    toc = []
    for chapter in chapter_ranges:
        # PyMuPDF uses 1-indexed page numbers for set_toc
        toc.append([1, chapter["title"], chapter["start_page"]])
    
    # Set the TOC (bookmarks)
    doc.set_toc(toc)
    
    # Save the modified PDF
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    
    return output_path
