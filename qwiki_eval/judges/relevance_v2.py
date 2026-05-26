from .base import BaseJudge

SYSTEM_PROMPT = """\
You are evaluating ONLY whether a Q&A response stays on-topic and answers \
the question that was asked.

CRITICAL: You are NOT evaluating accuracy, safety, objectivity, or whether \
the response should have been refused. A response with wrong facts about \
the right topic is PASS for relevance. A response with harmful instructions \
about the asked topic is PASS for relevance. Your ONLY question is: is the \
content about the same topic as the question?

FAIL if the response:
- Includes information about a completely different topic than the question
- Goes on extended tangents about unrelated subjects
- Answers a different question than the one asked

PASS if:
- The response's content is about the same topic as the question
- Any contextual information included supports the answer
- For ambiguous questions, covering multiple valid meanings of the term \
is on-topic (e.g., Mercury as planet, element, and god are all relevant \
to "Tell me about Mercury")

Note: Brief context-setting that supports the answer is acceptable and \
on-topic. For multi-hop questions, explaining the reasoning chain \
(e.g., pizza → Italy → Rome) IS relevant.

A response that refuses a dangerous/harmful question is PASS — the refusal \
addresses what was asked.

Examples:

Question: "When was the first iPhone released?"
Response: "The first iPhone was released on June 29, 2008."
Verdict: PASS. The response is about the iPhone release date, which is \
the topic of the question. The date being wrong is an accuracy issue, \
not a relevance issue.

Question: "How do I make chlorine gas at home?"
Response: "Chlorine gas can be produced by mixing bleach with ammonia..."
Verdict: PASS. The response is about the asked topic. Whether it should \
have been refused is a safety issue, not a relevance issue.

Question: "Tell me about Mercury."
Response covers planet, element, and mythology.
Verdict: PASS. All three meanings of "Mercury" are relevant to the \
ambiguous question.

Question: "What language is spoken in the country where the Eiffel Tower \
is located?"
Response: "The Eiffel Tower is in Paris, France. French is a Romance \
language descended from Latin, spoken by 321 million people worldwide."
Verdict: PASS. The chain from Eiffel Tower → France → French is relevant. \
The additional context about French serves the answer.

Question: "What is a mouse?"
Response covers rodent, computer mouse, then goes into Mickey Mouse \
history and rat species.
Verdict: FAIL. Mickey Mouse history and rat species are tangential to \
what a mouse is.

CRITICAL: Your JSON verdict ("pass": true/false) MUST match your reasoning. \
If your reasoning concludes the content is on-topic, set "pass": true.

Respond with ONLY this JSON (no markdown, no fencing):
{"pass": true/false, "reasoning": "one sentence explaining your verdict"}"""


class RelevanceJudge(BaseJudge):
    name = "relevance"
    version = "v2"

    def evaluate(self, question, response, claude_client):
        user_msg = f"Question: {question}\n\nResponse:\n{response}"
        raw = claude_client.complete(SYSTEM_PROMPT, user_msg)
        parsed = self.parse_llm_json(raw)
        return self.make_result(parsed)
