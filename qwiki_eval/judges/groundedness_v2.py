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

IMPORTANT: Preserve the grammatical structure of the original sentence. \
If a sentence says "X of Y including A, B, and C," extract it as ONE claim \
about X of Y with the listed items as examples — NOT as separate claims \
about X of A, X of B, X of C.

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

Response: "Six million Jews were murdered, along with millions of other \
victims including Roma people, disabled individuals, and political prisoners."
Claims:
1. Six million Jews were murdered
2. Millions of other victims were killed including Roma people, disabled \
individuals, and political prisoners
(Extract as ONE collective claim — do NOT split into "millions of Roma," \
"millions of disabled," etc.)

Respond with ONLY this JSON (no markdown, no fencing):
{"claims": ["claim 1", "claim 2", "claim 3"]}"""

GROUNDEDNESS_CHECK_PROMPT = """\
You are checking whether factual claims from a Q&A response are grounded \
in (i.e., supported by) the Wikipedia article text provided.

CRITICAL SCOPE BOUNDARY: You are evaluating ONLY groundedness — whether \
claims appear in the cited articles. You are NOT evaluating:
- Accuracy (whether claims are factually correct — that's the accuracy judge)
- Completeness (whether claims are comprehensive — that's the completeness judge)
- Safety, objectivity, or any other dimension

CRITICAL RULES:
1. You must ONLY use the Wikipedia article text provided below. Do NOT use \
your own knowledge or training data to judge whether a claim is grounded.
2. OMISSION IS NOT CONTRADICTION. This rule is absolute and cannot be \
overridden. A claim is GROUNDED if every person, fact, or item it names \
APPEARS in the article — regardless of whether the article names ADDITIONAL \
items. "Discovered by A and B" is GROUNDED when the article says \
"discovered by A, B, C, and D" because A and B are IN the article. The \
claim would ONLY be UNGROUNDED if A or B were NOT in the article at all. \
"A and B" does NOT mean "only A and B" — it simply does not mention C and \
D. Whether C and D should have been included is the completeness judge's \
job, NOT yours. Do NOT mark a claim UNGROUNDED because the article lists \
more items than the claim mentions.
3. You are NOT checking if the claims are factually correct — only whether \
they appear in the provided article text.
4. A paraphrase or reasonable rewording of article content IS grounded \
(doesn't need to be verbatim).
5. A fact that happens to be true but is NOT in any of the provided articles \
is UNGROUNDED — even if you know it's correct from your training data.
6. If the article directly contradicts a claim with a DIFFERENT value — such \
as different numbers (2,224 vs 2,208), different rankings ("largest" vs \
"second largest"), or different dates — the claim IS ungrounded. This is \
not an accuracy question; it is a groundedness question because the article \
explicitly states something different from the claim.
7. "Directly derivable" means the article discusses a SPECIFIC relationship \
between named entities that the claim also states. Example: if the article \
discusses Hollywood in the context of Los Angeles, then "Hollywood is in \
Los Angeles" is grounded. However, you must NOT derive unstated properties \
from definitions. If the article defines X but does not state property Y, \
you cannot infer Y — it must appear in the article text.
8. Read claims carefully for grammatical structure. "X of Y including A, B, \
and C" means X applies to the TOTAL of Y — it does NOT mean X of A, X of B, \
and X of C individually. Check the collective claim, not per-item \
interpretations.

NOTE: The article text provided may be a partial extract, not the complete \
Wikipedia article. If a claim describes a well-known application or use of \
the article's subject and the article title directly matches (e.g., an \
industrial application of a chemical compound, where the article is about \
that compound and discusses other applications), treat such claims as \
GROUNDED. But do NOT extend this tolerance to numbers, dates, rankings, or \
specific factual assertions — those must appear in the provided text.

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

Claim: "Tower cranes can reach heights of over 80 meters"
Article says: "Tower cranes can achieve a height under hook of over 100 metres"
Verdict: GROUNDED (over 100 metres certainly includes over 80 meters)

Claim: "Dynamite is an explosive invented by Alfred Nobel in 1867"
Article says: "Nobel invented dynamite in 1866" and "he patented it in 1867"
Verdict: UNGROUNDED. The claim says "invented...in 1867" but the article \
says the invention was in 1866. The year 1867 refers to the patent, not \
the invention. The claim misattributes the date to a different event.

Claim: "Fission was first discovered by Otto Hahn and Fritz Strassmann"
Article says: "discovered by Otto Hahn, Fritz Strassmann, Lise Meitner, \
and Otto Robert Frisch"
Verdict: GROUNDED. Both Hahn and Strassmann are named in the article. The \
response does not say "only" Hahn and Strassmann — it simply names two of \
the four discoverers. Omitting Meitner and Frisch is a completeness issue, \
not a groundedness issue. \
WRONG analysis: "The article attributes discovery to four scientists, not \
two, so this is UNGROUNDED." Naming a subset is not a contradiction.

Claim: "Cyanide has industrial applications in electroplating"
Article title: "Cyanide" — article discusses mining, chemical synthesis, \
and other industrial uses but electroplating not in the provided extract.
Verdict: GROUNDED (the article is about cyanide and covers its industrial \
applications — this specific application likely appears in a section not \
included in the extract)

Claim: "Millions of other victims including Roma, disabled, and political \
prisoners were killed"
Article says: ~190,000 disabled people killed, various numbers for other groups
Verdict: GROUNDED ("millions" modifies "other victims" as a collective total \
— the listed groups are examples within that total, not individually \
quantified as millions)

Claim: "Hollywood is located in Los Angeles, California"
Article discusses Hollywood in relation to the Los Angeles area within \
California, mentioning both in the same passages.
Verdict: GROUNDED (the relationship is clearly discussed in the article — \
it does not need to appear as a standalone sentence)

CRITICAL: Your JSON verdict ("pass": true/false) MUST match your analysis.
- If ANY claim is UNGROUNDED, set "pass": false.
- If ALL claims are GROUNDED, set "pass": true.
Double-check: count your GROUNDED and UNGROUNDED claims before writing the \
verdict. If the UNGROUNDED count is zero, the verdict MUST be true.

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
    version = "v2"

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
