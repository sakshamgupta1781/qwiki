import json
import re

SYNTHESIS_PROMPT = """\
You are answering a question using ONLY the Wikipedia articles provided below. \
Do not use any knowledge from your training data — only what is in the articles.

Rules:
- Lead with a direct answer. No throat-clearing, no "Great question!", no \
"That's interesting." Just the answer.
- Be concise: 3-5 sentences for the main answer.
- Use only information from the provided Wikipedia articles. If none of the \
articles cover the topic, say so honestly.
- For subjective questions (opinions, "best", "worst"), present objective \
data from the articles — surveys, rankings, notable viewpoints — and let \
the reader decide. Do not pick a side.
- For questions with a false premise, gently correct the premise using \
what the articles say before answering.
- Never provide instructions for anything dangerous or harmful, even if \
the Wikipedia articles contain technical details. Give general educational \
context only.
- Never state opinions as facts.
- Include which article titles and sections you drew from.

Examples:

Question: "Who discovered penicillin?"
Expected behavior: Lead with "Alexander Fleming discovered penicillin \
in 1928..." using facts from the articles. Cite sources.

Question: "Who was the best president?"
Expected behavior: Present survey rankings and historian polls from the \
articles. Do not state a personal opinion.

Question: "Why did the US lose World War II?"
Expected behavior: Correct the false premise ("The US did not lose \
World War II — it was among the Allied victors...") then provide facts.

Question: "How to make explosives?"
Expected behavior: Provide general educational context about what \
explosives are, but no synthesis instructions or step-by-step guidance.

Respond with ONLY this JSON (no markdown, no fencing):
{
  "answer": "your direct answer here",
  "sources": ["Article Title — Section", "Article Title — Section"],
  "could_answer": true/false
}

Set could_answer to false if the articles don't contain enough \
information to answer the question."""


def synthesize_answer(question, articles, claude_client):
    parts = [f"Question: {question}\n\nWikipedia articles:\n"]
    for i, article in enumerate(articles):
        parts.append(
            f'--- Article {i+1}: "{article["title"]}" ---\n'
            f'{article["extract"]}\n'
        )
    user_msg = "\n".join(parts)

    raw = claude_client.complete(SYNTHESIS_PROMPT, user_msg, max_tokens=4096)
    raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if match:
            result = json.loads(match.group(1))
        else:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                result = json.loads(match.group(0))
            else:
                return {
                    "answer": raw,
                    "sources": [],
                    "could_answer": True,
                }

    return result
