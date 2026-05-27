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
4. Do NOT use any web search, built-in search plugins, or external tools
5. Simply remove question words (who, what, when, where, why, how) \
and filler words (is, are, was, were, the, a, an, of, did, do, does)
6. Keep the remaining content words in order

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

Question: "What is the capital of the country where pizza was invented?"
RIGHT: "pizza invented country capital"

Respond with ONLY this JSON (no markdown, no fencing):
{"query": "simplified search terms"}"""

AMBIGUITY_CHECK_PROMPT = """\
Does this question contain a term with multiple well-known meanings?

CRITICAL CONSTRAINTS:
- Do NOT answer the question
- Do NOT use any web search, built-in search plugins, or external tools
- Do NOT include answers or facts beyond identifying the ambiguity
- ONLY identify whether the key term has multiple common meanings
- The search queries you suggest must use ONLY words from the question \
plus a disambiguation word (the meaning category itself)

Rules:
- Only flag genuinely ambiguous terms where a reader would wonder which \
meaning is intended
- Do NOT flag terms with one dominant meaning (e.g., "Einstein" is not \
ambiguous)
- Do NOT flag questions that specify the meaning (e.g., "What is the \
Python programming language?" is NOT ambiguous)
- Limit to 3-4 meanings maximum — only the most common ones

Examples:

Question: "What is Python?"
AMBIGUOUS: ["Python programming language", "Python snake", "Monty Python"]

Question: "What is Mercury?"
AMBIGUOUS: ["Mercury planet", "Mercury element", "Mercury mythology"]

Question: "Who discovered penicillin?"
NOT_AMBIGUOUS

Question: "Tell me about Jordan"
AMBIGUOUS: ["Jordan country", "Michael Jordan basketball"]

Question: "What does spring mean?"
AMBIGUOUS: ["spring season", "spring water source", "spring mechanical"]

Question: "What is the tallest building?"
NOT_AMBIGUOUS

Respond with ONLY this JSON (no markdown, no fencing):
{"ambiguous": true/false, "meanings": ["search query 1", "search query 2"]}"""


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


def check_ambiguity(question, claude_client):
    try:
        raw = claude_client.complete(AMBIGUITY_CHECK_PROMPT, f"Question: {question}")
        raw = raw.strip()
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                result = json.loads(match.group(0))
            else:
                return False, []
        if result.get("ambiguous", False):
            return True, result.get("meanings", [])
        return False, []
    except Exception:
        return False, []


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
            additional_results = wiki.search(meaning_query, limit=2)
            for result in additional_results:
                if result["title"] not in fetched_titles:
                    article = wiki.get_extract(result["title"])
                    if article["extract"]:
                        articles.append(article)
                        fetched_titles.add(result["title"])

    return articles, search_query
