import re
from urllib.parse import unquote

from .base import BaseJudge, JudgeResult
from ..api.mediawiki import MediaWikiClient

REFUSAL_CHECK_PROMPT = """\
Is this response a refusal to answer the question (e.g., declining due to \
safety, harmful content, or policy reasons)?

Respond with ONLY this JSON (no markdown, no fencing):
{"is_refusal": true/false}"""

RELEVANCE_PROMPT = """\
You are evaluating whether the Wikipedia sources cited in a Q&A response are \
relevant to the question and answer.

You will be given:
1. The original question
2. The response (answer + sources)
3. The intro text of each cited Wikipedia article

FAIL if:
- Any cited source is completely irrelevant to both the question and answer
- The sources don't cover the main topic of the question

PASS if:
- The cited sources are relevant to the question and support the answer
- Sources cover related sub-topics that contribute to the answer

Respond with ONLY this JSON (no markdown, no fencing):
{"pass": true/false, "reasoning": "one sentence"}"""

URL_PATTERN = re.compile(r'https?://en\.wikipedia\.org/wiki/[^\s\)"\',]+')


def extract_urls(text):
    return URL_PATTERN.findall(text)


def title_from_url(url):
    path = url.split("/wiki/", 1)[-1]
    path = path.split("#")[0]
    return unquote(path).replace("_", " ")


class SourceQualityJudge(BaseJudge):
    name = "source_quality"
    version = "v1"

    def evaluate(self, question, response, claude_client):
        urls = extract_urls(response)

        if not urls:
            user_msg = f"Question: {question}\n\nResponse:\n{response}"
            raw = claude_client.complete(REFUSAL_CHECK_PROMPT, user_msg)
            try:
                parsed = self.parse_llm_json(raw)
                if parsed.get("is_refusal", False):
                    return JudgeResult(
                        judge_name=self.name,
                        passed=True,
                        reasoning="Response is a refusal — sources not expected.",
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

        source_context = []
        for src in valid_sources:
            article = wiki.get_extract(src["title"])
            intro = article["extract"].split("\n\n")[0] if article["extract"] else ""
            source_context.append(f"Source: {src['url']}\nTitle: {src['title']}\nIntro: {intro}")

        user_msg = (
            f"Question: {question}\n\n"
            f"Response:\n{response}\n\n"
            f"Cited Wikipedia articles:\n\n" + "\n\n".join(source_context)
        )

        raw = claude_client.complete(RELEVANCE_PROMPT, user_msg)
        parsed = self.parse_llm_json(raw)
        return self.make_result(parsed, evidence=[s["url"] for s in valid_sources])
