# AGENTS.md

## Cursor Cloud specific instructions

This is a **single-module Python CLI tool** (学术论文爬虫工具) — no backend services, databases, or Docker required.

### Running the application

- Entry point: `python3 main.py` — runs a quick test via Semantic Scholar API
- Core module: `paper_crawler.py` — contains `search_semantic_scholar`, `search_arxiv`, `search_openalex`, `search_cnki`
- See `README.md` for usage examples

### Caveats

- **Semantic Scholar API rate limiting**: The API aggressively returns 429 (Too Many Requests). The built-in retry logic waits 60s per attempt. If running tests back-to-back, allow ~60s cooldown between Semantic Scholar calls. Use arXiv or OpenAlex APIs for faster iteration during development.
- **`pip install -e .` does not work** due to flat layout (multiple top-level modules). Install dependencies with `pip install requests beautifulsoup4 pandas openpyxl trafilatura` instead.
- **No linting/testing framework** is configured in this project. There are no test files, no `pytest`, no `flake8`/`ruff`/`mypy` config.
- **Network access required**: All 3 active data sources (Semantic Scholar, arXiv, OpenAlex) are external HTTP APIs.
- **Output files**: Search functions with `save=True` write `.xlsx` files to the working directory.
