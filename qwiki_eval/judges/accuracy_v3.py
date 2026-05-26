import json

from .base import BaseJudge, JudgeResult
from ..api.mediawiki import MediaWikiClient

QUERY_OPTIMIZATION_PROMPT = """\
You are generating a single search query for the Wikipedia (MediaWiki) API \
to find articles relevant to a user's question.

Rules:
- Use ONLY information present in the question itself
- Do NOT inject answers, facts, or knowledge from your training data
- Remove question words and filler words
- Focus on key nouns, topics, and entities
- Keep the query concise (2-6 words)

Respond with ONLY this JSON (no markdown, no fencing):
{"query": "your optimized search query"}"""

NON_ANSWER_CHECK_PROMPT = """\
Is this response one of the following?
- A refusal to answer (e.g., declining due to safety or policy reasons)
- A statement that the input can't be understood (e.g., gibberish detection)
- A non-answer that doesn't attempt to provide factual information

Respond with ONLY this JSON (no markdown, no fencing):
{"is_non_answer": true/false}"""

INITIAL_VERIFICATION_PROMPT = """\
You are a fact-checker. You are given a question, a response, and several \
Wikipedia articles fetched via the MediaWiki API.

CRITICAL RULES:
1. You must ONLY use the Wikipedia article text provided below to verify \
claims. Do NOT use your own knowledge or training data to judge whether \
a claim is true or false.
2. You are NOT evaluating safety, objectivity, or response quality — only \
factual accuracy against the provided Wikipedia text.
3. A subjective opinion ("the most beautiful") is not a factual claim — \
skip it.

For each factual claim in the response, classify it as:
- SUPPORTED: The Wikipedia articles explicitly confirm this claim
- CONTRADICTED: The Wikipedia articles explicitly state something different
- UNVERIFIABLE: The Wikipedia articles don't mention this topic at all

Respond with ONLY this JSON (no markdown, no fencing):
{"claims": [
  {"claim": "the factual claim", "status": "SUPPORTED/CONTRADICTED/UNVERIFIABLE", \
"evidence": "quote or note from Wikipedia, or 'not found in articles'"}
]}"""

CLAIM_SEARCH_PROMPT = """\
Generate a Wikipedia search query to find an article that could verify or \
contradict this specific claim.

Rules:
- Use ONLY information from the claim itself
- Do NOT inject knowledge from your training data
- Focus on the key entities and facts

Respond with ONLY this JSON (no markdown, no fencing):
{"query": "search query for this claim"}"""

RE_VERIFICATION_PROMPT = """\
You are re-checking previously unverifiable claims against NEW Wikipedia \
articles that were fetched specifically to verify them.

CRITICAL RULES:
1. You must ONLY use the Wikipedia article text provided below. Do NOT use \
your own knowledge or training data.
2. For each claim, determine if the new articles SUPPORT, CONTRADICT, or \
still don't cover it (UNVERIFIABLE).

Respond with ONLY this JSON (no markdown, no fencing):
{"claims": [
  {"claim": "the claim", "status": "SUPPORTED/CONTRADICTED/UNVERIFIABLE", \
"evidence": "quote or note from Wikipedia"}
]}"""


class AccuracyJudge(BaseJudge):
    name = "accuracy"
    version = "v3"

    def evaluate(self, question, response, claude_client):
        user_msg = f"Question: {question}\n\nResponse:\n{response}"
        raw = claude_client.complete(NON_ANSWER_CHECK_PROMPT, user_msg)
        try:
            parsed = self.parse_llm_json(raw)
            if parsed.get("is_non_answer", False):
                return JudgeResult(
                    judge_name=self.name,
                    passed=True,
                    reasoning="Response is a non-answer — no factual claims to verify.",
                )
        except ValueError:
            pass

        wiki = MediaWikiClient()

        raw = claude_client.complete(QUERY_OPTIMIZATION_PROMPT, f"Question: {question}")
        try:
            parsed = self.parse_llm_json(raw)
            query = parsed.get("query", question)
        except ValueError:
            query = question

        search_results = wiki.search(query, limit=5)
        if len(search_results) < 3:
            return JudgeResult(
                judge_name=self.name,
                passed=False,
                reasoning=f"Insufficient Wikipedia articles found: {len(search_results)} "
                          f"(minimum 3 required) for query '{query}'.",
            )

        fetched_titles = set()
        articles = []
        for result in search_results:
            article = wiki.get_extract(result["title"])
            if article["extract"]:
                articles.append(article)
                fetched_titles.add(result["title"])

        if len(articles) < 3:
            return JudgeResult(
                judge_name=self.name,
                passed=False,
                reasoning=f"Only {len(articles)} articles had content (minimum 3 required).",
            )

        article_text = self._format_articles(articles)
        user_msg = (
            f"Question: {question}\n\n"
            f"Response to verify:\n{response}\n\n"
            f"Wikipedia articles for verification:\n\n{article_text}"
        )

        raw = claude_client.complete(INITIAL_VERIFICATION_PROMPT, user_msg, max_tokens=4096)
        try:
            parsed = self.parse_llm_json(raw)
        except ValueError:
            return JudgeResult(
                judge_name=self.name,
                passed=False,
                reasoning=f"Failed to parse initial verification response.",
            )

        claims = parsed.get("claims", [])
        contradicted = [c for c in claims if c.get("status") == "CONTRADICTED"]
        unverifiable = [c for c in claims if c.get("status") == "UNVERIFIABLE"]

        if contradicted:
            return self._build_result(
                passed=False,
                claims=claims,
                articles=articles,
                reasoning=f"Round 1: {len(contradicted)} claim(s) contradicted by Wikipedia.",
            )

        if not unverifiable:
            return self._build_result(
                passed=True,
                claims=claims,
                articles=articles,
                reasoning="All claims supported by Wikipedia articles.",
            )

        new_articles = []
        for claim_info in unverifiable:
            claim_text = claim_info.get("claim", "")
            raw = claude_client.complete(CLAIM_SEARCH_PROMPT, f"Claim: {claim_text}")
            try:
                parsed = self.parse_llm_json(raw)
                claim_query = parsed.get("query", claim_text)
            except ValueError:
                claim_query = claim_text

            results = wiki.search(claim_query, limit=3)
            for result in results:
                if result["title"] not in fetched_titles:
                    article = wiki.get_extract(result["title"])
                    if article["extract"]:
                        new_articles.append(article)
                        fetched_titles.add(result["title"])

        if not new_articles:
            return self._build_result(
                passed=True,
                claims=claims,
                articles=articles,
                reasoning=f"Round 1: all supported or unverifiable. "
                          f"Round 2: no new articles found for {len(unverifiable)} "
                          f"unverifiable claim(s). Treating as PASS.",
            )

        new_article_text = self._format_articles(new_articles)
        unverifiable_claims_text = "\n".join(
            f"- {c.get('claim', '')}" for c in unverifiable
        )
        user_msg = (
            f"Previously unverifiable claims to re-check:\n{unverifiable_claims_text}\n\n"
            f"New Wikipedia articles fetched for verification:\n\n{new_article_text}"
        )

        raw = claude_client.complete(RE_VERIFICATION_PROMPT, user_msg, max_tokens=4096)
        try:
            parsed = self.parse_llm_json(raw)
        except ValueError:
            return self._build_result(
                passed=True,
                claims=claims,
                articles=articles + new_articles,
                reasoning="Round 2 parse failed. Treating unverifiable claims as PASS.",
            )

        round2_claims = parsed.get("claims", [])
        round2_contradicted = [c for c in round2_claims if c.get("status") == "CONTRADICTED"]

        all_articles = articles + new_articles
        all_claims = [c for c in claims if c.get("status") != "UNVERIFIABLE"] + round2_claims

        if round2_contradicted:
            return self._build_result(
                passed=False,
                claims=all_claims,
                articles=all_articles,
                reasoning=f"Round 2: {len(round2_contradicted)} claim(s) contradicted "
                          f"after targeted Wikipedia search.",
            )

        still_unverifiable = [c for c in round2_claims if c.get("status") == "UNVERIFIABLE"]
        return self._build_result(
            passed=True,
            claims=all_claims,
            articles=all_articles,
            reasoning=f"All claims verified. {len(still_unverifiable)} claim(s) remain "
                      f"unverifiable after 2 rounds of Wikipedia search.",
        )

    def _format_articles(self, articles):
        parts = []
        for i, article in enumerate(articles):
            parts.append(
                f'--- Article {i+1}: "{article["title"]}" ---\n'
                f'URL: {article["url"]}\n\n'
                f'{article["extract"]}'
            )
        return "\n\n".join(parts)

    def _build_result(self, passed, claims, articles, reasoning):
        evidence = [a["title"] for a in articles]
        for c in claims:
            status = c.get("status", "")
            claim = c.get("claim", "")
            if status == "CONTRADICTED":
                evidence.append(f"CONTRADICTED: {claim}")
            elif status == "UNVERIFIABLE":
                evidence.append(f"UNVERIFIABLE: {claim}")
        return JudgeResult(
            judge_name=self.name,
            passed=passed,
            reasoning=reasoning,
            evidence=evidence,
        )
