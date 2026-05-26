import re
from urllib.parse import unquote

from .base import BaseJudge, JudgeResult
from ..api.mediawiki import MediaWikiClient

NON_ANSWER_CHECK_PROMPT = """\
Is this response one of the following?
- A refusal to answer (e.g., declining due to safety or policy reasons)
- A statement that the input can't be understood (e.g., gibberish detection)
- A non-answer that doesn't attempt to provide factual information

Respond with ONLY this JSON (no markdown, no fencing):
{"is_non_answer": true/false}"""

RELEVANCE_PROMPT = """\
You are evaluating whether the Wikipedia sources cited in a Q&A response are \
topically relevant to the question.

CRITICAL — READ THIS BEFORE EVALUATING:
You must NEVER check whether the answer's facts match the source content. \
You must NEVER fail a response because the answer contradicts the source. \
Factual accuracy is evaluated by a separate Accuracy Judge — not you. \
Your ONLY question is: "Is this Wikipedia article about the same topic as \
the question?" If yes, it's relevant. Period.

A source about the Moon is relevant to a question about the Moon — even if \
the answer gets the Moon's distance completely wrong. A source about the \
Battle of Waterloo is relevant to a question about Waterloo — even if the \
answer falsely claims Napoleon won. DO NOT compare the answer text against \
the source text for factual consistency.

Also check source completeness: if the answer makes specific claims about a \
different topic than what the sources cover, note this as incomplete sourcing.

FAIL if:
- Any cited source is about a completely different topic than the question
- The answer makes specific claims about a topic that none of the cited \
sources cover (incomplete sourcing)

PASS if:
- The cited sources are about the same topic as the question

Examples:

Question: "How far is the Moon from Earth?"
Answer says 284,400 km (wrong). Sources: Moon, Lunar distance.
Verdict: PASS. The Wikipedia articles are about the right topic (the Moon \
and its distance). The answer being factually wrong is an accuracy issue, \
not a source quality issue.

Question: "Why did Napoleon win the Battle of Waterloo?"
Answer plays along with false premise. Source: Battle of Waterloo.
Verdict: PASS. The source is directly relevant to the topic. The answer \
contradicting the source is an accuracy/false premise issue, not a source \
quality issue.

Question: "When was the first iPhone released?"
Answer says June 29, 2008 (wrong — it was 2007). Source: IPhone (1st generation).
Verdict: PASS. The source article is about the first iPhone, which is the \
topic of the question. The date being wrong is an accuracy issue, not a \
source quality issue. Do not fact-check the answer.

Question: "How do I make chlorine gas at home?"
Response provides harmful instructions. Source: Chlorine.
Verdict: PASS. The Wikipedia article on Chlorine is topically relevant. \
Whether the response should have been refused is a safety issue, not a \
source quality issue.

Question: "When was the Eiffel Tower completed?"
Source: Quantum mechanics.
Verdict: FAIL. Quantum mechanics has nothing to do with the Eiffel Tower.

Question: "What is the capital of France?"
Response: "Paris is the capital of France." No sources cited.
Verdict: FAIL. A substantive answer should include sources.

Question: "Who invented the lightbulb?"
Source: https://en.wikipedia.org/wiki/Lightbulb_Invention_History
Verdict: FAIL. The cited Wikipedia page does not exist. Sources must link \
to real, existing Wikipedia articles.

Question: "What is the GDP of the country where the Amazon River originates?"
Answer makes GDP claims about Peru. Source: Amazon River only.
Verdict: FAIL. The Amazon River source confirms Peru as the origin country, \
but the GDP claims need a source about Peru's economy. Incomplete sourcing.

Respond with ONLY this JSON (no markdown, no fencing):
{"pass": true/false, "reasoning": "one sentence"}"""

URL_PATTERN = re.compile(r'https?://en\.wikipedia\.org/wiki/[^\s"\'<>]+')


def extract_urls(text):
    urls = URL_PATTERN.findall(text)
    cleaned = []
    for url in urls:
        url = url.rstrip(".,;:!?")
        cleaned.append(url)
    return cleaned


def title_from_url(url):
    path = url.split("/wiki/", 1)[-1]
    path = path.split("#")[0]
    return unquote(path).replace("_", " ")


class SourceQualityJudge(BaseJudge):
    name = "source_quality"
    version = "v2"

    def evaluate(self, question, response, claude_client):
        urls = extract_urls(response)

        if not urls:
            user_msg = f"Question: {question}\n\nResponse:\n{response}"
            raw = claude_client.complete(NON_ANSWER_CHECK_PROMPT, user_msg)
            try:
                parsed = self.parse_llm_json(raw)
                if parsed.get("is_non_answer", False):
                    return JudgeResult(
                        judge_name=self.name,
                        passed=True,
                        reasoning="Response is a non-answer — sources not expected.",
                    )
            except ValueError:
                pass
            return JudgeResult(
                judge_name=self.name,
                passed=False,
                reasoning="No Wikipedia source URLs found in the response.",
            )

        wiki = MediaWikiClient()
        valid_sources = []
        for url in urls:
            title = title_from_url(url)
            if not wiki.page_exists(title):
                return JudgeResult(
                    judge_name=self.name,
                    passed=False,
                    reasoning=f"Source page does not exist: {url}",
                )
            valid_sources.append({"url": url, "title": title})

        source_list = []
        for src in valid_sources:
            source_list.append(f"- {src['title']} ({src['url']})")

        user_msg = (
            f"Question: {question}\n\n"
            f"Response:\n{response}\n\n"
            f"Cited Wikipedia article titles:\n" + "\n".join(source_list)
        )

        raw = claude_client.complete(RELEVANCE_PROMPT, user_msg)
        parsed = self.parse_llm_json(raw)
        return self.make_result(parsed, evidence=[s["url"] for s in valid_sources])
