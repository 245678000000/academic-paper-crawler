from paper_crawler import (
    search_semantic_scholar,
    search_arxiv,
    search_openalex,
    search_cnki
)

def main():
    print("=" * 60)
    print("  学术论文爬虫工具 v1.0（2026 中国版）")
    print("=" * 60)
    print()
    print("可用函数：")
    print("  search_semantic_scholar(query, limit=20)  - Semantic Scholar 搜索")
    print("  search_arxiv(query, limit=20)             - arXiv 搜索")
    print("  search_openalex(query, limit=20)          - OpenAlex 搜索")
    print("  search_cnki(query, limit=10)              - CNKI 搜索（高风险）")
    print()

    print("--- 快速测试 (Semantic Scholar) ---")
    df = search_semantic_scholar("large language model", limit=3, save=False)
    if not df.empty:
        print(f"\n示例结果（前3篇）：")
        for i, row in df.iterrows():
            print(f"\n  [{i+1}] {row['title']}")
            print(f"      作者: {str(row['authors'])[:60]}...")
            print(f"      年份: {row['year']}  引用: {row['citation_count']}")
    else:
        print("未获取到结果，可能是网络问题。")


if __name__ == "__main__":
    main()
