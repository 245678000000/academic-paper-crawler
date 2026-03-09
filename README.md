# 学术论文爬虫工具 v1.0（2026 中国版）

基于 Python 的学术论文搜索和抓取工具，支持多个学术数据源 API。

## 支持的数据源

| 优先级 | 数据源 | 说明 |
|--------|--------|------|
| 1 | Semantic Scholar API | 推荐首选，免费、覆盖2亿+论文 |
| 2 | arXiv API | STEM预印本最强 |
| 3 | OpenAlex API | 开源学术图谱，含大量中文论文 |
| 4 | CNKI（中国知网） | 高风险，仅提供安全建议 |

## 快速开始

```bash
pip install requests beautifulsoup4 pandas openpyxl
python main.py
```

## 使用示例

```python
from paper_crawler import search_semantic_scholar, search_arxiv, search_openalex

df = search_semantic_scholar("deep learning", limit=20)
df = search_arxiv("transformer attention", limit=10)
df = search_openalex("自然语言处理", limit=15)
```

## 标准输出字段

title, authors, year, abstract, doi, pdf_url, citation_count, keywords, source, query

## 核心原则

- 优先使用官方免费 API
- 每次请求 sleep 随机 2-5 秒
- 自动重试 + 退避机制
- 出错时优雅处理并打印提示
- 仅限个人学习研究使用
