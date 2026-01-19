"""Command-line interface for PDF to Chapters."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from pdf_to_chapters.pdf_utils import (
    add_bookmarks_to_pdf,
    extract_bookmarks,
    get_chapter_page_ranges,
    get_total_pages,
    split_pdf_by_chapters,
)
from pdf_to_chapters.ai_utils import get_primary_chapters_from_ai, parse_toc_with_ai
from pdf_to_chapters.toc_utils import (
    extract_toc_text,
    calculate_page_offset,
    convert_toc_to_chapter_ranges,
)
from pdf_to_chapters.utils import format_bookmarks_for_ai, sanitize_filename


# Load environment variables from .env file
load_dotenv()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Split PDF into chapters based on bookmarks using AI inference",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i textbook.pdf
  %(prog)s -i textbook.pdf -o ./output
  %(prog)s --input book.pdf --output-dir ./chapters
        """
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to the input PDF file"
    )
    parser.add_argument(
        "--output-dir", "-o",
        help="Output directory (default: folder named after PDF in same location)"
    )
    parser.add_argument(
        "--api-key", "-k",
        help="API key (can also use OPENAI_API_KEY env var or .env file)"
    )
    parser.add_argument(
        "--api-url", "-u",
        help="API base URL (can also use OPENAI_URL env var or .env file)"
    )
    parser.add_argument(
        "--list-bookmarks", "-l",
        action="store_true",
        help="Just list all bookmarks and exit"
    )
    parser.add_argument(
        "--add-bookmarks", "-b",
        action="store_true",
        help="Add chapter bookmarks to the PDF instead of splitting (for PDFs without bookmarks)"
    )
    
    return parser.parse_args()


def process_with_bookmarks(
    pdf_path: Path,
    bookmarks: list[dict],
    total_pages: int,
    api_key: str,
    api_url: str,
    model: str,
    list_only: bool
) -> list[dict]:
    """Process a PDF that has bookmarks."""
    print(f"Found {len(bookmarks)} bookmarks")
    
    # Just list bookmarks if requested
    if list_only:
        print("\nBookmark structure:")
        print(format_bookmarks_for_ai(bookmarks))
        sys.exit(0)
    
    # Get primary chapters from AI
    print("\nAnalyzing bookmarks with AI to identify primary chapters...")
    primary_chapters = get_primary_chapters_from_ai(bookmarks, api_key, api_url, model)
    
    if not primary_chapters:
        print("Error: Could not identify any primary chapters")
        sys.exit(1)
    
    print(f"\nIdentified {len(primary_chapters)} primary chapters:")
    for ch in primary_chapters:
        print(f"  - {ch}")
    
    return get_chapter_page_ranges(bookmarks, primary_chapters, total_pages)


def process_without_bookmarks(
    pdf_path: Path,
    total_pages: int,
    api_key: str,
    api_url: str,
    model: str,
    list_only: bool
) -> list[dict]:
    """Process a PDF that has no bookmarks using TOC extraction."""
    print("No bookmarks found, attempting to extract chapters from Table of Contents...")
    
    if list_only:
        # Extract and show TOC text instead
        toc_text, toc_start = extract_toc_text(str(pdf_path))
        print(f"\nTOC text extracted starting from PDF page {toc_start}:")
        print(toc_text[:5000] if len(toc_text) > 5000 else toc_text)
        sys.exit(0)
    
    # Extract TOC text
    toc_text, toc_start = extract_toc_text(str(pdf_path))
    if not toc_text:
        print("Error: Could not find Table of Contents in PDF")
        sys.exit(1)
    
    print(f"  Found TOC starting on PDF page {toc_start}")
    
    # Parse TOC with AI
    print("\nAnalyzing TOC with AI to identify chapters and page numbers...")
    toc_chapters = parse_toc_with_ai(toc_text, api_key, api_url, model)
    
    if not toc_chapters:
        print("Error: Could not parse chapters from TOC")
        sys.exit(1)
    
    print(f"\nIdentified {len(toc_chapters)} primary chapters from TOC:")
    for ch in toc_chapters:
        print(f"  - {ch['title']} (TOC page {ch['toc_page']})")
    
    # Calculate page offset
    print("\nCalculating page offset...")
    offset = calculate_page_offset(str(pdf_path), toc_chapters)
    
    return convert_toc_to_chapter_ranges(toc_chapters, offset, total_pages)


def main():
    """Main entry point."""
    args = parse_args()
    
    # Get API configuration from args, env vars, or .env file (only needed if not listing bookmarks)
    api_key = None
    api_url = None
    model = None
    if not args.list_bookmarks:
        api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("Error: API key required. Use --api-key or set OPENAI_API_KEY in .env file")
            sys.exit(1)
        api_url = args.api_url or os.environ.get("OPENAI_URL", "https://api.z.ai/api/paas/v4")
        model = os.environ.get("OPENAI_MODEL", "glm-4.7")
    
    # Validate input file
    pdf_path = Path(args.input)
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    if not pdf_path.suffix.lower() == ".pdf":
        print(f"Error: File must be a PDF: {pdf_path}")
        sys.exit(1)
    
    # Extract bookmarks
    print(f"Extracting bookmarks from: {pdf_path.name}")
    bookmarks = extract_bookmarks(str(pdf_path))
    total_pages = get_total_pages(str(pdf_path))
    
    # Process based on whether bookmarks exist
    if bookmarks:
        chapter_ranges = process_with_bookmarks(
            pdf_path, bookmarks, total_pages, api_key, api_url, model, args.list_bookmarks
        )
    else:
        chapter_ranges = process_without_bookmarks(
            pdf_path, total_pages, api_key, api_url, model, args.list_bookmarks
        )
    
    if not chapter_ranges:
        print("Error: Could not determine page ranges for chapters")
        sys.exit(1)
    
    # Handle --add-bookmarks mode: inject bookmarks instead of splitting
    if args.add_bookmarks:
        # Determine output path
        if args.output_dir:
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{pdf_path.stem}_bookmarked.pdf"
        else:
            output_path = pdf_path.parent / f"{pdf_path.stem}_bookmarked.pdf"
        
        print(f"\nAdding {len(chapter_ranges)} chapter bookmarks to PDF...")
        add_bookmarks_to_pdf(str(pdf_path), chapter_ranges, str(output_path))
        print(f"\nDone! Created bookmarked PDF: {output_path}")
        return
    
    # Setup output directory - always create folder named after the textbook
    pdf_name = sanitize_filename(pdf_path.stem)
    if args.output_dir:
        output_dir = Path(args.output_dir) / pdf_name
    else:
        output_dir = pdf_path.parent / pdf_name
    
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")
    
    # Split PDF
    print("\nSplitting PDF into chapters...")
    output_files = split_pdf_by_chapters(str(pdf_path), chapter_ranges, output_dir)
    
    print(f"\nDone! Created {len(output_files)} chapter PDF files.")


if __name__ == "__main__":
    main()
