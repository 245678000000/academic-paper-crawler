import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
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

MAX_RETRIES = 3
RATE_LIMIT_WAIT = 60


def _safe_get(url, params=None, headers=None, timeout=30, retries=MAX_RETRIES):
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, headers=headers or HEADERS, timeout=timeout)

            if resp.status_code == 429:
                wait_time = RATE_LIMIT_WAIT * (attempt + 1)
                print(f"⚠️ 请求过于频繁 (429)，等待 {wait_time} 秒后重试（第 {attempt+1}/{retries} 次）...")
                time.sleep(wait_time)
                continue

            if resp.status_code >= 500:
                wait_time = 10 * (attempt + 1)
                print(f"⚠️ 服务器错误 ({resp.status_code})，等待 {wait_time} 秒后重试（第 {attempt+1}/{retries} 次）...")
                time.sleep(wait_time)
                continue

            resp.raise_for_status()
            return resp

        except requests.exceptions.Timeout:
            print(f"⚠️ 请求超时，第 {attempt+1}/{retries} 次重试...")
            time.sleep(5 * (attempt + 1))
        except requests.exceptions.ConnectionError:
            print(f"⚠️ 连接失败，第 {attempt+1}/{retries} 次重试...")
            time.sleep(5 * (attempt + 1))
        except requests.exceptions.RequestException as e:
            print(f"❌ 请求出错: {e}")
            return None

    print("❌ 已达到最大重试次数，放弃请求。")
    return None


def _save_results(df, prefix, query):
    if df.empty:
        return
    today = datetime.now().strftime("%Y%m%d")
    safe_query = query.replace(" ", "_")[:30]
    filename = f"papers_{prefix}_{safe_query}_{today}.xlsx"
    df.to_excel(filename, index=False, engine="openpyxl")
    print(f"📁 已保存到: {filename}")


def search_semantic_scholar(query, limit=20, save=True):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "fields": "title,authors,year,abstract,externalIds,openAccessPdf,citationCount,s2FieldsOfStudy"
    }

    results = []
    offset = 0

    while len(results) < limit:
        params["offset"] = offset
        params["limit"] = min(limit - len(results), 100)

        print(f"[Semantic Scholar] 正在搜索: {query}（已获取 {len(results)} 篇）")
        resp = _safe_get(url, params=params)

        if resp is None:
            break

        try:
            data = resp.json()
        except ValueError:
            print("❌ 响应解析失败（非 JSON）")
            break

        if not data.get("data"):
            print("没有更多结果了。")
            break

        for paper in data["data"]:
            try:
                authors = ", ".join([a.get("name", "") for a in paper.get("authors", [])])
                ext_ids = paper.get("externalIds") or {}
                doi = ext_ids.get("DOI", "")
                pdf_url = ""
                oa_pdf = paper.get("openAccessPdf")
                if oa_pdf:
                    pdf_url = oa_pdf.get("url", "")
                keywords = ", ".join([f.get("category", "") for f in paper.get("s2FieldsOfStudy", []) if f.get("category")])

                results.append({
                    "title": paper.get("title", ""),
                    "authors": authors,
                    "year": paper.get("year", ""),
                    "abstract": paper.get("abstract", "") or "",
                    "doi": doi,
                    "pdf_url": pdf_url,
                    "citation_count": paper.get("citationCount", 0),
                    "keywords": keywords,
                    "source": "Semantic Scholar",
                    "query": query
                })
            except (TypeError, AttributeError) as e:
                print(f"⚠️ 跳过一条解析异常的记录: {e}")
                continue

        offset += len(data["data"])
        if offset >= data.get("total", 0):
            break

        time.sleep(random.uniform(2, 5))

    df = pd.DataFrame(results, columns=STANDARD_COLUMNS)
    print(f"✅ 共获取 {len(df)} 篇论文")

    if save:
        _save_results(df, "ss", query)

    return df


def search_arxiv(query, limit=20, save=True):
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

        print(f"[arXiv] 正在搜索: {query}（已获取 {len(results)} 篇）")
        resp = _safe_get(url, params=params)

        if resp is None:
            break

        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as e:
            print(f"❌ XML 解析失败: {e}")
            break

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)

        if not entries:
            print("没有更多结果了。")
            break

        for entry in entries:
            try:
                title_el = entry.find("atom:title", ns)
                title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else ""

                author_els = entry.findall("atom:author", ns)
                author_names = []
                for a in author_els:
                    name_el = a.find("atom:name", ns)
                    if name_el is not None and name_el.text:
                        author_names.append(name_el.text)
                authors = ", ".join(author_names)

                pub_el = entry.find("atom:published", ns)
                published = pub_el.text[:4] if pub_el is not None and pub_el.text else ""

                abs_el = entry.find("atom:summary", ns)
                abstract = abs_el.text.strip().replace("\n", " ") if abs_el is not None and abs_el.text else ""

                pdf_url = ""
                for link in entry.findall("atom:link", ns):
                    if link.get("title") == "pdf":
                        pdf_url = link.get("href", "")

                doi = ""
                arxiv_doi = entry.find("{http://arxiv.org/schemas/atom}doi")
                if arxiv_doi is not None and arxiv_doi.text:
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
            except (TypeError, AttributeError) as e:
                print(f"⚠️ 跳过一条解析异常的记录: {e}")
                continue

        start += len(entries)
        time.sleep(random.uniform(2, 5))

    df = pd.DataFrame(results, columns=STANDARD_COLUMNS)
    print(f"✅ 共获取 {len(df)} 篇论文")

    if save:
        _save_results(df, "arxiv", query)

    return df


def search_cnki(query, limit=10, save=True):
    print("=" * 60)
    print("⚠️  CNKI 高风险抓取模式")
    print("⚠️  仅限公开摘要，严禁批量下载全文")
    print("⚠️  中国用户：建议使用代理IP，避免校园网/机构网被封")
    print("=" * 60)

    print(f"\n[CNKI] 搜索关键词: {query}")
    print("⚠️  CNKI 反爬极严，纯 requests 方式无法完成搜索。")
    print("⚠️  此函数为安全提示桩函数，不执行实际抓取。")
    print(f"\n📝 CNKI 安全搜索建议：")
    print(f"   方案一（推荐）：手动操作")
    print(f"   1. 打开 https://www.cnki.net/")
    print(f"   2. 搜索关键词: {query}")
    print(f"   3. 手动导出为 Excel/CSV")
    print(f"   4. 这是最安全、最可靠的方式")
    print(f"\n   方案二：使用 Selenium + 手动验证码")
    print(f"   需额外安装 selenium 和 webdriver-manager")
    print(f"\n💡 替代方案：使用 OpenAlex API 搜索中文论文（完全免费安全）")
    print(f"   调用：search_openalex('{query}', limit={limit})")

    return pd.DataFrame(columns=STANDARD_COLUMNS)


def search_openalex(query, limit=20, save=True):
    url = "https://api.openalex.org/works"
    results = []
    page = 1
    per_page = min(limit, 50)

    while len(results) < limit:
        params = {
            "search": query,
            "page": page,
            "per_page": min(per_page, limit - len(results)),
            "mailto": "research@example.com"
        }

        print(f"[OpenAlex] 正在搜索: {query}（已获取 {len(results)} 篇）")
        resp = _safe_get(url, params=params)

        if resp is None:
            break

        try:
            data = resp.json()
        except ValueError:
            print("❌ 响应解析失败（非 JSON）")
            break

        works = data.get("results", [])
        if not works:
            print("没有更多结果了。")
            break

        for work in works:
            try:
                title = work.get("title", "") or ""
                authorships = work.get("authorships", [])
                authors = ", ".join([
                    a.get("author", {}).get("display_name", "")
                    for a in authorships
                    if a.get("author")
                ])
                year = work.get("publication_year", "")
                doi = work.get("doi", "") or ""
                if doi.startswith("https://doi.org/"):
                    doi = doi.replace("https://doi.org/", "")

                pdf_url = ""
                best_oa = work.get("best_oa_location")
                if best_oa and isinstance(best_oa, dict):
                    pdf_url = best_oa.get("pdf_url", "") or ""

                abstract_index = work.get("abstract_inverted_index")
                abstract = ""
                if abstract_index and isinstance(abstract_index, dict):
                    word_positions = []
                    for word, positions in abstract_index.items():
                        if isinstance(positions, list):
                            for pos in positions:
                                word_positions.append((pos, word))
                    word_positions.sort()
                    abstract = " ".join([w for _, w in word_positions])

                citation_count = work.get("cited_by_count", 0)
                concepts = work.get("concepts", []) or []
                keywords = ", ".join([c.get("display_name", "") for c in concepts[:5] if c.get("display_name")])

                results.append({
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "abstract": abstract,
                    "doi": doi,
                    "pdf_url": pdf_url,
                    "citation_count": citation_count,
                    "keywords": keywords,
                    "source": "OpenAlex",
                    "query": query
                })
            except (TypeError, AttributeError, KeyError) as e:
                print(f"⚠️ 跳过一条解析异常的记录: {e}")
                continue

        page += 1
        time.sleep(random.uniform(2, 5))

    df = pd.DataFrame(results, columns=STANDARD_COLUMNS)
    print(f"✅ 共获取 {len(df)} 篇论文")

    if save:
        _save_results(df, "openalex", query)

    return df


if __name__ == "__main__":
    print("=" * 60)
    print("  学术论文爬虫工具 v1.0（2026 中国版）")
    print("=" * 60)
    print()
    print("可用函数：")
    print("  search_semantic_scholar(query, limit=20)  - Semantic Scholar 搜索")
    print("  search_arxiv(query, limit=20)             - arXiv 搜索")
    print("  search_openalex(query, limit=20)          - OpenAlex 搜索")
    print("  search_cnki(query, limit=10)              - CNKI 搜索（安全提示）")
    print()
    print("示例：")
    print('  df = search_semantic_scholar("deep learning", limit=10)')
    print('  df = search_arxiv("transformer attention", limit=5)')
    print()

    print("\n--- 运行快速测试 (Semantic Scholar) ---")
    df = search_semantic_scholar("large language model", limit=3, save=False)
    if not df.empty:
        print(f"\n示例结果（前3篇）：")
        for i, row in df.iterrows():
            print(f"\n  [{i+1}] {row['title']}")
            print(f"      作者: {str(row['authors'])[:60]}...")
            print(f"      年份: {row['year']}  引用: {row['citation_count']}")
    else:
        print("未获取到结果，可能是网络或速率限制问题。")
