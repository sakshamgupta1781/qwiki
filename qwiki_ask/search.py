from qwiki_common.mediawiki import MediaWikiClient


def search_and_fetch(search_query, original_question):
    wiki = MediaWikiClient()

    search_results = wiki.search(search_query, limit=5)

    if not search_results:
        simplified = original_question.split()[:3]
        search_results = wiki.search(" ".join(simplified), limit=5)

    if not search_results:
        return []

    articles = []
    for result in search_results:
        article = wiki.get_extract(result["title"])
        if article["extract"]:
            articles.append(article)

    return articles
