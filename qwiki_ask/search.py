import json
import re

from qwiki_common.mediawiki import MediaWikiClient

QUERY_OPTIMIZATION_PROMPT = """\
Make this question search-friendly for the Wikipedia API by removing \
unnecessary words. Your job is ONLY to simplify the query — NOT to \
answer the question.

CRITICAL RULES:
1. Use ONLY words that appear in the question itself
2. Do NOT add names, answers, or facts from your training data
3. Do NOT hint at or include the answer in the search query
4. Simply remove question words (who, what, when, where, why, how) \
and filler words (is, are, was, were, the, a, an, of, did, do, does)
5. Keep the remaining content words in order

Examples:

Question: "Who invented the lightbulb and when did they die?"
WRONG: "Thomas Edison lightbulb invention history"
RIGHT: "invented lightbulb"
Why: "Thomas Edison" is the ANSWER — do not include it.

Question: "Who discovered penicillin?"
WRONG: "Alexander Fleming penicillin discovery"
RIGHT: "penicillin discovery"
Why: "Alexander Fleming" is the ANSWER — do not include it.

Question: "What is the tallest building in the world?"
RIGHT: "tallest building world"

Question: "When did humans first land on the Moon?"
RIGHT: "humans first land Moon"

Question: "Why did the Roman Empire fall?"
RIGHT: "Roman Empire fall"

Question: "What is the capital of the country where pizza was invented?"
RIGHT: "pizza invented country capital"

Respond with ONLY this JSON (no markdown, no fencing):
{"query": "simplified search terms"}"""


def optimize_query(question, claude_client):
    try:
        raw = claude_client.complete(QUERY_OPTIMIZATION_PROMPT, f"Question: {question}")
        raw = raw.strip()

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                result = json.loads(match.group(0))
            else:
                return question

        return result.get("query", question)
    except Exception:
        return question


def search_and_fetch(question, claude_client):
    search_query = optimize_query(question, claude_client)

    wiki = MediaWikiClient()
    search_results = wiki.search(search_query, limit=5)

    if not search_results:
        simplified = question.split()[:3]
        search_results = wiki.search(" ".join(simplified), limit=5)

    if not search_results:
        return [], search_query

    articles = []
    for result in search_results:
        article = wiki.get_extract(result["title"])
        if article["extract"]:
            articles.append(article)

    return articles, search_query
