"""AI/API utilities for chapter inference."""

import json
import re

from openai import OpenAI

from pdf_to_chapters.utils import format_bookmarks_for_ai


def get_ai_client(api_key: str, base_url: str) -> OpenAI:
    """Create and return an OpenAI client configured for the API."""
    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        default_headers={
            "HTTP-Referer": "https://cline.bot",
            "X-Title": "Cline"
        }
    )


def get_primary_chapters_from_ai(bookmarks: list[dict], api_key: str, base_url: str) -> list[str]:
    """Use AI to identify the primary/top-level chapters from bookmarks."""
    client = get_ai_client(api_key, base_url)
    
    bookmarks_text = format_bookmarks_for_ai(bookmarks)
    
    prompt = f"""Analyze the following PDF bookmark structure and identify ONLY the primary/main chapters.

Rules:
1. Focus on top-level chapters (typically level 1 or 2 bookmarks)
2. Ignore sub-sections, appendices, index, table of contents, preface, acknowledgments, and similar front/back matter
3. Return ONLY the main content chapters that a reader would consider the core material
4. Return the chapter titles EXACTLY as they appear in the bookmark list
5. Return your answer as a JSON array of strings containing the exact chapter titles

Bookmark structure:
{bookmarks_text}

Return ONLY a valid JSON array of chapter titles, nothing else. Example format:
["Chapter 1: Introduction", "Chapter 2: Getting Started", "Chapter 3: Advanced Topics"]"""

    response = client.chat.completions.create(
        model="glm-4.7",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that analyzes document structures. Always respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )
    
    response_text = response.choices[0].message.content.strip()
    
    # Try to parse JSON from response
    try:
        # Handle potential markdown code blocks
        if "```" in response_text:
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                response_text = json_match.group(1)
        
        chapters = json.loads(response_text)
        if isinstance(chapters, list):
            return [str(ch) for ch in chapters]
    except json.JSONDecodeError:
        pass
    
    # Fallback: try to extract chapter titles from text
    print("Warning: Could not parse AI response as JSON, attempting fallback extraction")
    chapters = []
    for line in response_text.split("\n"):
        line = line.strip().strip("-").strip("*").strip('"').strip()
        if line and any(bm["title"] == line for bm in bookmarks):
            chapters.append(line)
    
    return chapters


def parse_toc_with_ai(toc_text: str, api_key: str, base_url: str) -> list[dict]:
    """
    Use AI to parse TOC text and extract chapter titles with their page numbers.
    Returns list of dicts with 'title' and 'toc_page' keys.
    """
    client = get_ai_client(api_key, base_url)
    
    prompt = f"""Analyze the following Table of Contents extracted from a PDF and identify the PRIMARY/MAIN chapters.

Rules:
1. Focus on main chapters only (numbered chapters like "1 Introduction", "Chapter 2: Methods", etc.)
2. Ignore sub-sections, appendices, index, preface, acknowledgments, bibliography, and similar front/back matter
3. For each chapter, extract the chapter title and its page number as shown in the TOC
4. The page numbers in the TOC are the BOOK's page numbers, not PDF page numbers
5. Return as a JSON array of objects with "title" and "toc_page" fields

TOC Text:
{toc_text}

Return ONLY a valid JSON array. Example format:
[{{"title": "1 Introduction", "toc_page": 1}}, {{"title": "2 Linear Algebra", "toc_page": 31}}]"""

    response = client.chat.completions.create(
        model="glm-4.7",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that parses document structures. Always respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )
    
    response_text = response.choices[0].message.content.strip()
    
    # Try to parse JSON from response
    try:
        # Handle potential markdown code blocks
        if "```" in response_text:
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                response_text = json_match.group(1)
        
        chapters = json.loads(response_text)
        if isinstance(chapters, list):
            return [{"title": str(ch.get("title", "")), "toc_page": int(ch.get("toc_page", 0))} for ch in chapters]
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        print(f"Warning: Could not parse AI response as JSON: {e}")
    
    return []
