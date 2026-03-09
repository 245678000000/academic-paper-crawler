# 学术论文爬虫工具

## 项目概述
基于 Python 的学术论文搜索和抓取工具，支持多个学术数据源 API，遵循 2026 中国版爬虫规范。

## 技术栈
- Python 3.11
- requests（API 调用）
- beautifulsoup4（网页解析）
- pandas + openpyxl（数据处理和 Excel 导出）

## 项目结构
- `main.py` - 主入口，运行快速测试
- `paper_crawler.py` - 核心爬虫模块，包含所有搜索函数
- `.agents/skills/academic-paper-crawler/SKILL.md` - Agent Skill 规范文档

## 可用函数
- `search_semantic_scholar(query, limit)` - Semantic Scholar API 搜索
- `search_arxiv(query, limit)` - arXiv API 搜索
- `search_openalex(query, limit)` - OpenAlex API 搜索
- `search_cnki(query, limit)` - CNKI 搜索（高风险，建议手动）

## 数据源优先级
1. Semantic Scholar API（首选）
2. arXiv API（STEM 预印本）
3. OpenAlex API（含中文论文）
4. CNKI（高风险，需谨慎）

## 输出格式
Excel (.xlsx) 文件，包含标准字段：title, authors, year, abstract, doi, pdf_url, citation_count, keywords, source, query
