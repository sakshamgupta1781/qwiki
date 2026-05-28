import re
from urllib.parse import unquote

from .base import BaseJudge, JudgeResult
from ..api.mediawiki import MediaWikiClient

URL_PATTERN = re.compile(r'https?://en\.wikipedia\.org/wiki/[^\s"\'<>]+')

CLAIM_EXTRACTION_PROMPT = """\
Extract every discrete factual claim from this Q&A response as a numbered list.

A factual claim is any statement that asserts something as true — names, \
dates, numbers, events, relationships, descriptions, measurements.

Do NOT extract:
- Subjective opinions ("the most beautiful", "arguably the greatest")
- Caveats ("I cannot provide real-time data", "Wikipedia may not have...")
- Meta-statements ("Based on the available articles", "According to Wikipedia")
- Question restatements ("The question asks about...")
- Source citations ("Sources: Penicillin — History")

Examples:

Response: "Alexander Fleming discovered penicillin in 1928 when he noticed \
mold killing bacteria in a petri dish."
Claims:
1. Alexander Fleming discovered penicillin
2. The discovery was in 1928
3. He noticed mold killing bacteria in a petri dish

Response: "I cannot provide today's bitcoin price, but historically Bitcoin \
reached $100,000 in December 2024."
Claims:
1. Bitcoin reached $100,000 in December 2024
(Skip: "I cannot provide today's bitcoin price" is a caveat, not a claim)

Respond with ONLY this JSON (no markdown, no fencing):
{"claims": ["claim 1", "claim 2", "claim 3"]}"""

GROUNDEDNESS_CHECK_PROMPT = """\
You are checking whether factual claims from a Q&A response are grounded \
in (i.e., supported by) the Wikipedia article text provided.

CRITICAL RULES:
1. You must ONLY use the Wikipedia article text provided below. Do NOT use \
your own knowledge or training data to judge whether a claim is grounded.
2. You are NOT checking if the claims are factually correct — only whether \
they appear in the provided article text.
3. A paraphrase or reasonable rewording of article content IS grounded \
(doesn't need to be verbatim).
4. A fact that happens to be true but is NOT in any of the provided articles \
is UNGROUNDED — even if you know it's correct from your training data.

For each claim, classify as:
- GROUNDED: The claim appears in or is directly derivable from the articles
- UNGROUNDED: The claim does NOT appear in any of the provided articles

Examples:

Claim: "Tokyo has a population of about 14 million"
Article says: "population of the city proper is 13.96 million"
Verdict: GROUNDED (reasonable paraphrase of 13.96 million)

Claim: "Fleming was born in Lochfield, Scotland on August 6, 1881"
Articles provided are about Penicillin and its history — no mention of \
Fleming's birthplace or birth date.
Verdict: UNGROUNDED (this fact is not in any provided article — it may \
have come from training data)

Claim: "Penicillin has saved over 200 million lives"
No article contains this statistic.
Verdict: UNGROUNDED (fabricated or training-data statistic)

Claim: "The discovery led to the development of antibiotics"
Article says: "penicillin... led to an era of antibiotics"
Verdict: GROUNDED (paraphrase of article content)

CRITICAL: Your JSON verdict ("pass": true/false) MUST match your analysis. \
If ANY claim is UNGROUNDED, set "pass": false.

Respond with ONLY this JSON (no markdown, no fencing):
{"pass": true/false, "claims": [
  {"claim": "the claim text", "status": "GROUNDED/UNGROUNDED", \
"evidence": "quote from article or 'not found'"}
], "reasoning": "summary of verdict"}"""


def _extract_urls(text):
    urls = URL_PATTERN.findall(text)
    return [url.rstrip(".,;:!?") for url in urls]


def _title_from_url(url):
    path = url.split("/wiki/", 1)[-1].split("#")[0]
    return unquote(path).replace("_", " ")


class GroundednessJudge(BaseJudge):
    name = "groundedness"
    version = "v1"

    def evaluate(self, question, response, claude_client):
        urls = _extract_urls(response)

        if not urls:
            return JudgeResult(
                judge_name=self.name,
                passed=True,
                reasoning="No Wikipedia sources cited — likely a refusal. "
                          "No factual claims to verify groundedness.",
            )

        wiki = MediaWikiClient()
        articles = []
        for url in urls:
            title = _title_from_url(url)
            article = wiki.get_extract(title)
            if article["extract"]:
                articles.append(article)

        if not articles:
            return JudgeResult(
                judge_name=self.name,
                passed=False,
                reasoning="Cited sources could not be fetched from Wikipedia.",
            )

        user_msg = f"Question: {question}\n\nResponse:\n{response}"
        raw = claude_client.complete(CLAIM_EXTRACTION_PROMPT, user_msg)
        try:
            parsed = self.parse_llm_json(raw)
            claims = parsed.get("claims", [])
        except ValueError:
            return JudgeResult(
                judge_name=self.name,
                passed=False,
                reasoning="Failed to extract claims from response.",
            )

        if not claims:
            return JudgeResult(
                judge_name=self.name,
                passed=True,
                reasoning="No factual claims found in the response.",
            )

        article_text = []
        for i, article in enumerate(articles):
            article_text.append(
                f'--- Article {i+1}: "{article["title"]}" ---\n'
                f'{article["extract"]}'
            )

        claims_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(claims))
        user_msg = (
            f"Claims to check:\n{claims_text}\n\n"
            f"Wikipedia articles (cited as sources in the response):\n\n"
            + "\n\n".join(article_text)
        )

        raw = claude_client.complete(GROUNDEDNESS_CHECK_PROMPT, user_msg, max_tokens=4096)
        try:
            parsed = self.parse_llm_json(raw)
        except ValueError:
            return JudgeResult(
                judge_name=self.name,
                passed=False,
                reasoning="Failed to parse groundedness check response.",
            )

        checked_claims = parsed.get("claims", [])
        ungrounded = [c for c in checked_claims if c.get("status") == "UNGROUNDED"]

        evidence = [a["title"] for a in articles]
        for c in ungrounded:
            evidence.append(f"UNGROUNDED: {c.get('claim', '')}")

        return JudgeResult(
            judge_name=self.name,
            passed=not bool(ungrounded),
            reasoning=parsed.get("reasoning", f"{len(ungrounded)} ungrounded claim(s)"),
            evidence=evidence,
        )
