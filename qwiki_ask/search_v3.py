import json
import re

from qwiki_common.mediawiki import MediaWikiClient
from .search_v2 import optimize_query, check_ambiguity

DEEP_SEARCH_PROMPT = """\
The first Wikipedia search did not return articles that could answer \
the user's question. Your job is to generate a BETTER search query \
that might find the right Wikipedia article.

CRITICAL RULES:
1. Do NOT answer the question or hint at the answer
2. Do NOT use any web search, built-in search plugins, or external tools
3. Do NOT use your training data to inject facts or answers
4. Look at what went wrong with the first search and fix it
5. You may resolve indirect references if they are implied by the question \
(e.g., "capital of Japan" implies Tokyo — using "Tokyo" is not answer leaking, \
it's resolving the reference to find the right article)

Examples:

Question: "Why is the sky blue?"
First query: "sky blue"
Articles returned: Sky blue (color), Sky Blue Sky (album), Blue Sky Studios
Problem: the query matched the color name and media titles, not the science
Refined query: "sky color atmosphere light scattering"

Question: "How big is the capital of Japan?"
First query: "capital Japan size"
Articles returned: Capital punishment in Japan, Capital flows in Japan
Problem: "capital" was interpreted as financial/legal, not geographic
Refined query: "Tokyo area population geography"

Question: "What household chemicals should never be mixed together?"
First query: "household chemicals mixed together"
Articles returned: Pulp, Sodium chloride, Chemical warfare
Problem: too generic, didn't find safety/toxicology articles
Refined query: "household chemical reactions dangerous mixing bleach ammonia"

Question: "What's the population of the city where the Eiffel Tower is?"
First query: "Eiffel Tower city population"
Articles returned: Paris Tennessee, Tianducheng
Problem: matched wrong Paris and Eiffel Tower replicas
Refined query: "Paris France population demographics"

Respond with ONLY this JSON (no markdown, no fencing):
{"refined_query": "better search terms"}"""


def deep_search(question, first_query, existing_articles, claude_client):
    existing_titles = {a["title"] for a in existing_articles}

    user_msg = (
        f"Question: {question}\n"
        f"First search query: \"{first_query}\"\n"
        f"Articles returned: {', '.join(existing_titles)}\n"
        f"These articles did not contain enough information to answer the question."
    )

    try:
        raw = claude_client.complete(DEEP_SEARCH_PROMPT, user_msg)
        raw = raw.strip()
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                result = json.loads(match.group(0))
            else:
                return existing_articles, first_query
        refined_query = result.get("refined_query", "")
    except Exception:
        return existing_articles, first_query

    if not refined_query:
        return existing_articles, first_query

    wiki = MediaWikiClient()
    new_results = wiki.search(refined_query, limit=5)

    new_articles = list(existing_articles)
    for r in new_results:
        if r["title"] not in existing_titles:
            article = wiki.get_extract(r["title"])
            if article["extract"]:
                new_articles.append(article)
                existing_titles.add(r["title"])

    return new_articles, refined_query


def search_and_fetch(question, claude_client):
    search_query = optimize_query(question, claude_client)

    wiki = MediaWikiClient()
    search_results = wiki.search(search_query, limit=5)

    if not search_results:
        simplified = question.split()[:3]
        search_results = wiki.search(" ".join(simplified), limit=5)

    if not search_results:
        return [], search_query

    fetched_titles = set()
    articles = []
    for result in search_results:
        article = wiki.get_extract(result["title"])
        if article["extract"]:
            articles.append(article)
            fetched_titles.add(result["title"])

    is_ambiguous, meanings = check_ambiguity(question, claude_client)

    if is_ambiguous and meanings:
        for meaning_query in meanings:
            additional = wiki.search(meaning_query, limit=2)
            for result in additional:
                if result["title"] not in fetched_titles:
                    article = wiki.get_extract(result["title"])
                    if article["extract"]:
                        articles.append(article)
                        fetched_titles.add(result["title"])

    return articles, search_query
