"""Shared utility functions."""

import re


def sanitize_filename(name: str) -> str:
    """Sanitize a string to be used as a filename."""
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    # Limit length
    return sanitized[:100] if len(sanitized) > 100 else sanitized


def format_bookmarks_for_ai(bookmarks: list[dict]) -> str:
    """Format bookmarks as a structured list for the AI prompt."""
    lines = []
    for bm in bookmarks:
        indent = "  " * (bm["level"] - 1)
        lines.append(f"{indent}[Level {bm['level']}] {bm['title']} (Page {bm['page']})")
    return "\n".join(lines)
