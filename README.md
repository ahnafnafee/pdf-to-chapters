# PDF to Chapters

**Split PDF textbooks and ebooks into organized chapter files using AI-powered bookmark analysis.**

A Python CLI tool that automatically extracts chapters from PDF files based on bookmarks or table of contents, using AI to intelligently identify primary chapters and ignore sub-sections.

## ✨ Features

- **Bookmark-based extraction** — Analyzes PDF bookmarks to identify main chapters
- **TOC fallback** — Automatically extracts chapters from Table of Contents for PDFs without bookmarks
- **AI-powered analysis** — Uses LLM to distinguish primary chapters from sub-sections, appendices, and front matter
- **Smart page offset** — Calculates correct page mappings for accurate chapter splitting
- **Organized output** — Creates a folder per book with sequentially numbered chapter PDFs

## 📋 Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- OpenAI-compatible API key (supports ZhipuAI, OpenAI, or any compatible provider)

## 🚀 Installation

```bash
git clone https://github.com/yourusername/pdf-to-chapters.git
cd pdf-to-chapters
uv sync
```

## ⚙️ Configuration

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Add your API credentials:

```env
OPENAI_URL=https://api.z.ai/api/paas/v4
OPENAI_API_KEY=your_api_key_here
```

## 📖 Usage

```bash
# Basic usage
uv run pdf_to_chapters.py -i textbook.pdf

# Specify output directory
uv run pdf_to_chapters.py -i textbook.pdf -o ./output

# Preview bookmarks without splitting
uv run pdf_to_chapters.py -i textbook.pdf --list-bookmarks

# Add bookmarks to PDF instead of splitting (for PDFs without bookmarks)
uv run pdf_to_chapters.py -i textbook.pdf --add-bookmarks
```

### Command Options

| Option                 | Description                                                                    |
| ---------------------- | ------------------------------------------------------------------------------ |
| `-i, --input`          | Path to input PDF file (required)                                              |
| `-o, --output-dir`     | Output directory (default: same as input)                                      |
| `-k, --api-key`        | API key (or use OPENAI_API_KEY env var)                                        |
| `-u, --api-url`        | API base URL (or use OPENAI_URL env var)                                       |
| `-l, --list-bookmarks` | List bookmarks/TOC without splitting                                           |
| `-b, --add-bookmarks`  | Add chapter bookmarks to PDF instead of splitting (for PDFs without bookmarks) |

## 📁 Output Structure

Each PDF creates a folder with numbered chapter files:

```
output/
└── Machine Learning Textbook/
    ├── 01_Introduction.pdf
    ├── 02_Linear Algebra.pdf
    ├── 03_Probability Theory.pdf
    └── ...
```

## 🔧 How It Works

1. **Bookmark extraction** — Reads PDF bookmarks if available
2. **TOC fallback** — Extracts text from table of contents pages if no bookmarks
3. **AI analysis** — Sends bookmark/TOC structure to LLM to identify main chapters
4. **Page offset calculation** — For TOC-based extraction, finds actual PDF pages
5. **Chapter splitting** — Creates individual PDF files for each chapter

## 📄 License

MIT
