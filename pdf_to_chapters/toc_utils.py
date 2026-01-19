"""Table of Contents extraction and page offset calculation utilities."""

import re
from collections import Counter

import fitz  # PyMuPDF


def extract_toc_text(pdf_path: str, max_pages: int = 20) -> tuple[str, int]:
    """
    Extract text from the first pages of the PDF to find TOC.
    Returns the TOC text and the PDF page number where TOC starts (1-indexed).
    
    Detection methods:
    1. Look for pages containing 'contents' or 'table of contents'
    2. Look for pages with section numbering patterns (e.g., "1.1", "2.3.4") 
       combined with page numbers
    3. Look for pages with common chapter/section keywords followed by numbers
    """
    doc = fitz.open(pdf_path)
    toc_text = []
    toc_start_page = None
    
    # Patterns that indicate TOC content:
    # 1. Section numbers like "1.1", "2.3", "3.2.1" 
    section_pattern = re.compile(r'\b\d+\.\d+(?:\.\d+)?\b')
    # 2. Page numbers at end of lines or after titles
    page_num_pattern = re.compile(r'\s\d{1,3}(?:\s|$|\n)')
    # 3. Common TOC keywords
    toc_keywords = ['chapter', 'preface', 'introduction', 'appendix', 'index', 'exercises']
    
    for i in range(min(max_pages, doc.page_count)):
        text = doc[i].get_text()
        text_lower = text.lower()
        
        # Method 1: Look for explicit TOC indicators
        has_contents_header = any(
            indicator in text_lower 
            for indicator in ['contents', 'table of contents']
        )
        
        # Method 2: Heuristic - look for TOC-like patterns
        # A TOC page typically has:
        # - Multiple section numbers (1.1, 1.2, 2.1, etc.)
        # - Multiple page numbers 
        # - Keywords like chapter, preface, etc.
        section_matches = len(section_pattern.findall(text))
        page_num_matches = len(page_num_pattern.findall(text))
        keyword_matches = sum(1 for kw in toc_keywords if kw in text_lower)
        
        # Consider it a TOC page if:
        # - Has section patterns AND page numbers
        # - OR has TOC keywords AND page numbers
        has_toc_pattern = (
            (section_matches >= 3 and page_num_matches >= 5) or
            (keyword_matches >= 2 and page_num_matches >= 5) or
            (section_matches >= 5)  # Many section numbers alone is strong indicator
        )
        
        if has_contents_header or has_toc_pattern:
            if toc_start_page is None:
                toc_start_page = i + 1  # 1-indexed
            toc_text.append(f"=== PDF Page {i + 1} ===\n{text}")
        elif toc_start_page is not None:
            # Continue collecting pages after TOC starts (might span multiple pages)
            # Check if this page also looks like TOC continuation
            still_toc = (section_matches >= 2 or page_num_matches >= 3)
            if still_toc or len(toc_text) < 3:
                if len(toc_text) < 15:  # TOC shouldn't be more than ~15 pages
                    toc_text.append(f"=== PDF Page {i + 1} ===\n{text}")
                else:
                    break
            else:
                # Likely past the TOC
                break
    
    doc.close()
    return "\n\n".join(toc_text), toc_start_page or 1


def find_chapter_start_page(pdf_path: str, chapter_title: str, search_range: tuple[int, int] = (10, 100)) -> int | None:
    """
    Search for the actual PDF page where a chapter starts by looking for the chapter title.
    Starts from page 10 to skip TOC pages. Looks for chapter headings at the start of pages.
    Returns the 1-indexed PDF page number or None if not found.
    """
    doc = fitz.open(pdf_path)
    start, end = search_range
    
    # Extract chapter number if present (e.g., "1 Introduction" -> "1")
    chapter_num_match = re.match(r'^(\d+)\s+', chapter_title)
    
    # Clean title for matching (remove common prefixes, get first few meaningful words)
    clean_title = re.sub(r'^(chapter\s*)?\d*\.?\s*', '', chapter_title, flags=re.IGNORECASE).strip()
    # Get first 3-4 words for matching
    title_words = clean_title.split()[:4]
    title_pattern = r'\s+'.join(re.escape(w) for w in title_words) if title_words else None
    
    for i in range(start - 1, min(end, doc.page_count)):
        text = doc[i].get_text()
        first_block = text[:800].strip()  # Check more text for chapter detection
        
        # Method 1: Look for "Chapter X" patterns at the very start
        if chapter_num_match:
            chapter_num = chapter_num_match.group(1)
            # Pattern: "Chapter X" at the very start of the page
            if re.match(rf'^Chapter\s+{chapter_num}\b', first_block, re.IGNORECASE):
                doc.close()
                return i + 1
            # Pattern: Just the number as a heading followed by title
            lines = first_block.split('\n')
            if len(lines) >= 2:
                if lines[0].strip() == f"Chapter {chapter_num}" or lines[0].strip() == chapter_num:
                    doc.close()
                    return i + 1
        
        # Method 2: Look for chapter title words + "Chapter Outline" pattern (common in textbooks)
        if title_pattern and re.search(title_pattern, first_block, re.IGNORECASE):
            # Verify this is a chapter start by looking for chapter outline or similar markers
            if re.search(r'chapter\s+outline|learning\s+outcome|introduction', first_block, re.IGNORECASE):
                doc.close()
                return i + 1
        
        # Method 3: Look for exact title match in first few lines (for descriptive chapter names)
        if clean_title and len(clean_title) > 10:
            # Check if the first ~40 chars of the clean title appear in first 500 chars
            title_start = clean_title[:40].lower()
            if title_start in first_block[:500].lower():
                # Verify with chapter markers
                if re.search(r'chapter\s+outline|figure\s+\d|learning', first_block, re.IGNORECASE):
                    doc.close()
                    return i + 1
    
    doc.close()
    return None


def calculate_page_offset(pdf_path: str, toc_chapters: list[dict]) -> int:
    """
    Calculate the offset between TOC page numbers and actual PDF page numbers.
    offset = actual_pdf_page - toc_page
    
    Tries to find multiple chapters to validate the offset.
    """
    if not toc_chapters:
        return 0
    
    doc = fitz.open(pdf_path)
    offsets_found = []
    
    # Try to find chapters in the PDF - check first few chapters
    for idx, ch in enumerate(toc_chapters[:5]):  # Check up to first 5 chapters
        chapter_num = idx + 1  # Assume chapters are numbered 1, 2, 3...
        
        # Search in a range around where we expect the chapter
        search_start = max(10, ch["toc_page"])
        search_end = min(ch["toc_page"] + 50, doc.page_count)
        
        for page_idx in range(search_start - 1, search_end):
            text = doc[page_idx].get_text()
            first_block = text[:1000].strip()
            
            # Method 1: Look for "Figure X.1" pattern (common in textbooks)
            if re.search(rf'Figure\s+{chapter_num}\.1\b', first_block):
                if re.search(r'Chapter\s+Outline', first_block, re.IGNORECASE):
                    actual_page = page_idx + 1
                    offset = actual_page - ch["toc_page"]
                    offsets_found.append(offset)
                    print(f"  Found chapter {chapter_num} via Figure pattern: TOC page {ch['toc_page']} -> PDF page {actual_page} (offset {offset})")
                    break
            
            # Method 2: Look for "Chapter X" or "X.1 Section" patterns at page start
            if re.match(rf'^(Chapter\s+)?{chapter_num}\b', first_block, re.IGNORECASE):
                actual_page = page_idx + 1
                offset = actual_page - ch["toc_page"]
                offsets_found.append(offset)
                print(f"  Found chapter {chapter_num} via Chapter pattern: TOC page {ch['toc_page']} -> PDF page {actual_page} (offset {offset})")
                break
            
            # Method 3: Look for "X.1 Section Title" after Chapter Outline
            if re.search(r'Chapter\s+Outline', first_block, re.IGNORECASE):
                if re.search(rf'\b{chapter_num}\.1\s+\w', first_block):
                    actual_page = page_idx + 1
                    offset = actual_page - ch["toc_page"]
                    offsets_found.append(offset)
                    print(f"  Found chapter {chapter_num} via Outline pattern: TOC page {ch['toc_page']} -> PDF page {actual_page} (offset {offset})")
                    break
    
    doc.close()
    
    if offsets_found:
        # Use the most common offset (mode)
        offset = Counter(offsets_found).most_common(1)[0][0]
        print(f"  Using page offset: {offset}")
        return offset
    
    # Fallback: estimate based on typical front matter
    print("  Warning: Could not find chapters, using estimated offset of 16")
    return 16


def convert_toc_to_chapter_ranges(toc_chapters: list[dict], offset: int, total_pages: int) -> list[dict]:
    """Convert TOC chapters to chapter_ranges with actual PDF pages."""
    chapter_ranges = []
    
    for i, ch in enumerate(toc_chapters):
        actual_start = ch["toc_page"] + offset
        # End page is either next chapter start - 1, or total_pages
        if i + 1 < len(toc_chapters):
            actual_end = toc_chapters[i + 1]["toc_page"] + offset - 1
        else:
            actual_end = total_pages
        
        if actual_start > 0 and actual_start <= actual_end <= total_pages:
            chapter_ranges.append({
                "title": ch["title"],
                "start_page": actual_start,
                "end_page": actual_end
            })
    
    return chapter_ranges
