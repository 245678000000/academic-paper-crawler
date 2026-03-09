---
name: academic-paper-crawler
description: 学术论文爬虫规范，用于搜索和抓取学术论文数据。当用户要求抓取论文、搜索学术文献、爬取arXiv/Semantic Scholar/CNKI论文时使用此技能。
---

# 学术论文爬虫规范（2026 中国版）

## 1. 核心原则（必须严格遵守）

- **优先使用官方免费 API**（最稳、不被封）
- 只有 API 不够时才考虑轻度抓取公开页面
- 尊重 robots.txt 和网站条款，只用于个人学习研究
- 每次请求 sleep 随机 2-5 秒
- 必须加真实浏览器 User-Agent
- 出错时优雅处理并打印提示

## 2. 推荐优先级（按顺序使用）

| 优先级 | 数据源 | 说明 |
|--------|--------|------|
| 1 | **Semantic Scholar API** | 推荐首选，免费、覆盖2亿+论文、带摘要/引用/PDF链接 |
| 2 | **arXiv API** | STEM预印本最强，官方公开、支持搜索+全文 |
| 3 | **OpenAlex API** | 开源学术图谱，含大量中文论文 |
| 4 | **Crossref / PubMed** | Crossref 覆盖 DOI 元数据；PubMed 覆盖医学文献 |
| 5 | **CNKI（中国知网）** | ⚠️ 高风险！仅限公开摘要页，严禁批量下载全文，容易被封IP，建议用 Selenium + 手动验证码备用 |
| 6 | **万方数据 / 维普** | 国内学术数据库，需机构授权，API 接入有限，建议手动导出 |

## 3. 必须提取的标准字段（列名统一）

每篇论文必须包含以下字段，缺失时填空字符串：

| 字段名 | 说明 |
|--------|------|
| `title` | 标题 |
| `authors` | 作者列表，逗号分隔 |
| `year` | 年份 |
| `abstract` | 摘要 |
| `doi` | DOI |
| `pdf_url` | PDF直链（如果有） |
| `citation_count` | 引用数 |
| `keywords` | 关键词 |
| `source` | 来源：Semantic Scholar / arXiv / CNKI 等 |
| `query` | 搜索关键词 |

## 4. 技术栈要求

- **Python + requests**（API 调用）
- **beautifulsoup4**（网页抓取时）
- **pandas**（存 Excel，编码 utf-8-sig）
- 可选：`arxiv` 库、`semanticscholar` 库
- 存档路径：`papers_{关键词}_{日期}.csv` 或 `.xlsx`

## 5. 示例代码模板

### 5.1 Semantic Scholar API 搜索并保存

```python
import requests
import pandas as pd
import time
import random
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

STANDARD_COLUMNS = [
    "title", "authors", "year", "abstract", "doi",
    "pdf_url", "citation_count", "keywords", "source", "query"
]


def search_semantic_scholar(query, limit=20, save=True):
    """用 Semantic Scholar API 搜索论文"""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": min(limit, 100),
        "fields": "title,authors,year,abstract,externalIds,openAccessPdf,citationCount,s2FieldsOfStudy"
    }

    results = []
    offset = 0

    while len(results) < limit:
        params["offset"] = offset
        params["limit"] = min(limit - len(results), 100)

        try:
            print(f"[Semantic Scholar] 正在搜索: {query}（已获取 {len(results)} 篇）")
            resp = requests.get(url, params=params, headers=HEADERS, timeout=30)

            if resp.status_code == 429:
                print("⚠️ 请求过于频繁，等待 60 秒...")
                time.sleep(60)
                continue

            resp.raise_for_status()
            data = resp.json()

            if not data.get("data"):
                print("没有更多结果了。")
                break

            for paper in data["data"]:
                authors = ", ".join([a.get("name", "") for a in paper.get("authors", [])])
                doi = paper.get("externalIds", {}).get("DOI", "")
                pdf_url = ""
                if paper.get("openAccessPdf"):
                    pdf_url = paper["openAccessPdf"].get("url", "")
                keywords = ", ".join([f.get("category", "") for f in paper.get("s2FieldsOfStudy", [])])

                results.append({
                    "title": paper.get("title", ""),
                    "authors": authors,
                    "year": paper.get("year", ""),
                    "abstract": paper.get("abstract", ""),
                    "doi": doi,
                    "pdf_url": pdf_url,
                    "citation_count": paper.get("citationCount", 0),
                    "keywords": keywords,
                    "source": "Semantic Scholar",
                    "query": query
                })

            offset += len(data["data"])
            if offset >= data.get("total", 0):
                break

            time.sleep(random.uniform(2, 5))

        except requests.exceptions.RequestException as e:
            print(f"❌ 请求出错: {e}")
            break

    df = pd.DataFrame(results, columns=STANDARD_COLUMNS)
    print(f"✅ 共获取 {len(df)} 篇论文")

    if save and not df.empty:
        today = datetime.now().strftime("%Y%m%d")
        safe_query = query.replace(" ", "_")[:30]
        filename = f"papers_{safe_query}_{today}.xlsx"
        df.to_excel(filename, index=False, engine="openpyxl")
        print(f"📁 已保存到: {filename}")

    return df
```

### 5.2 arXiv API 搜索

```python
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time
import random
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

STANDARD_COLUMNS = [
    "title", "authors", "year", "abstract", "doi",
    "pdf_url", "citation_count", "keywords", "source", "query"
]


def search_arxiv(query, limit=20, save=True):
    """用 arXiv API 搜索论文"""
    url = "http://export.arxiv.org/api/query"
    results = []
    start = 0
    batch_size = min(limit, 50)

    while len(results) < limit:
        params = {
            "search_query": f"all:{query}",
            "start": start,
            "max_results": min(batch_size, limit - len(results)),
            "sortBy": "relevance",
            "sortOrder": "descending"
        }

        try:
            print(f"[arXiv] 正在搜索: {query}（已获取 {len(results)} 篇）")
            resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()

            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", ns)

            if not entries:
                print("没有更多结果了。")
                break

            for entry in entries:
                title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
                authors = ", ".join([a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)])
                published = entry.find("atom:published", ns).text[:4]
                abstract = entry.find("atom:summary", ns).text.strip().replace("\n", " ")

                pdf_url = ""
                for link in entry.findall("atom:link", ns):
                    if link.get("title") == "pdf":
                        pdf_url = link.get("href", "")

                doi = ""
                arxiv_doi = entry.find("{http://arxiv.org/schemas/atom}doi")
                if arxiv_doi is not None:
                    doi = arxiv_doi.text

                categories = entry.find("{http://arxiv.org/schemas/atom}primary_category")
                keywords = categories.get("term", "") if categories is not None else ""

                results.append({
                    "title": title,
                    "authors": authors,
                    "year": published,
                    "abstract": abstract,
                    "doi": doi,
                    "pdf_url": pdf_url,
                    "citation_count": "",
                    "keywords": keywords,
                    "source": "arXiv",
                    "query": query
                })

            start += len(entries)
            time.sleep(random.uniform(2, 5))

        except requests.exceptions.RequestException as e:
            print(f"❌ 请求出错: {e}")
            break

    df = pd.DataFrame(results, columns=STANDARD_COLUMNS)
    print(f"✅ 共获取 {len(df)} 篇论文")

    if save and not df.empty:
        today = datetime.now().strftime("%Y%m%d")
        safe_query = query.replace(" ", "_")[:30]
        filename = f"papers_arxiv_{safe_query}_{today}.xlsx"
        df.to_excel(filename, index=False, engine="openpyxl")
        print(f"📁 已保存到: {filename}")

    return df
```

### 5.3 CNKI 轻度抓取（带警告）

```python
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.cnki.net/"
}

STANDARD_COLUMNS = [
    "title", "authors", "year", "abstract", "doi",
    "pdf_url", "citation_count", "keywords", "source", "query"
]


def search_cnki(query, limit=10, save=True):
    """
    ⚠️ CNKI 轻度抓取 - 高风险警告 ⚠️

    风险提示：
    1. CNKI 反爬非常严格，频繁请求会被封 IP
    2. 仅限抓取公开摘要页，严禁批量下载全文 PDF
    3. 可能需要验证码，建议配合 Selenium + 手动操作
    4. 中国用户注意：高校/机构网络被封后影响范围大，建议使用个人网络+代理
    5. 仅限个人学习研究使用
    """
    print("=" * 60)
    print("⚠️  CNKI 高风险抓取模式")
    print("⚠️  仅限公开摘要，严禁批量下载全文")
    print("⚠️  中国用户：建议使用代理IP，避免校园网/机构网被封")
    print("=" * 60)

    search_url = "https://kns.cnki.net/kns8s/brief/grid"
    results = []

    try:
        session = requests.Session()
        session.headers.update(HEADERS)

        print(f"[CNKI] 正在搜索: {query}")
        print("⚠️  CNKI 搜索需要 Cookie 和验证码，纯 requests 方式成功率较低")
        print("⚠️  建议方案：使用 Selenium 打开浏览器手动登录后再抓取")

        print(f"\n📝 CNKI 手动搜索建议：")
        print(f"   1. 打开 https://www.cnki.net/")
        print(f"   2. 搜索关键词: {query}")
        print(f"   3. 手动导出为 Excel/CSV")
        print(f"   4. 这是最安全、最可靠的方式")

        return pd.DataFrame(columns=STANDARD_COLUMNS)

    except Exception as e:
        print(f"❌ CNKI 抓取失败: {e}")
        print("建议：改用 Semantic Scholar 或 OpenAlex 搜索中文论文")
        return pd.DataFrame(columns=STANDARD_COLUMNS)
```

## 6. 使用方法

以后只需要说以下指令，Agent 就会严格按照本规范执行：

- **"按学术论文爬虫规范，抓 20 篇关于 XX 的论文"**
  → Agent 会优先用 Semantic Scholar API 搜索，自动保存到 Excel

- **"用 arXiv 爬 10 篇机器学习论文并存 Excel"**
  → Agent 会用 arXiv API 搜索，保存为 `papers_arxiv_machine_learning_日期.xlsx`

- **"用 CNKI 搜索 XX 论文"**
  → Agent 会提醒风险，建议手动操作或改用其他 API

- **"搜索中文论文关于 XX"**
  → Agent 会优先用 OpenAlex API（含大量中文论文），再用 Semantic Scholar

## 7. 执行流程

Agent 收到论文抓取指令后，必须按以下流程执行：

1. 确认搜索关键词和数量
2. 根据优先级选择数据源（默认 Semantic Scholar）
3. 调用对应函数，加入 sleep 和错误处理
4. 提取标准字段，存入 DataFrame
5. 保存为 Excel（编码 utf-8-sig）
6. 打印摘要信息（数量、文件路径）

## 8. CNKI / 国内数据库风险提示（中国用户专用）

> **🚨 中国用户特别注意：**
>
> - 国内高校和科研机构的 IP 段被 CNKI/万方/维普重点监控
> - 一旦触发反爬，可能导致整个机构 IP 被封禁，影响全校师生正常使用
> - 建议使用个人网络（手机热点等）+ 代理 IP 进行测试
> - 优先使用 CNKI/万方/维普的官方导出功能（手动操作最安全）
> - 如果必须自动化，使用 Selenium + 随机延迟（10-30秒）+ 手动过验证码
> - **强烈建议：中文论文优先使用 OpenAlex API，覆盖量大且完全免费安全**
> - 注意遵守《数据安全法》《个人信息保护法》等法律法规，仅限学术研究使用
> - 部分高校已因批量下载被 CNKI 暂停服务，后果严重
