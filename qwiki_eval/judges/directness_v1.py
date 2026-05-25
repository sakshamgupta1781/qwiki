from .base import BaseJudge

SYSTEM_PROMPT = """\
You are evaluating whether a Q&A response leads directly with factual content \
or has unnecessary preamble before the answer.

FAIL if the response starts with any of the following before providing \
substantive information:
- Greetings or pleasantries ("Great question!", "Sure!", "Hello!", "Thanks for asking!")
- Hedging openers ("Well, that's an interesting topic...", "That depends on...")
- Self-referential statements ("As an AI...", "Let me help you with that", \
"I'd be happy to help")
- Meta-commentary about the question ("This is a complex topic", \
"There's a lot to unpack here")
- Throat-clearing phrases ("So,", "Interestingly,", "It's worth noting that")

PASS if the first sentence contains substantive information that directly \
addresses the question.

Note: A response that refuses to answer a dangerous/harmful question is \
considered PASS for directness — the refusal itself is the direct response.

Respond with ONLY this JSON (no markdown, no fencing):
{"pass": true/false, "reasoning": "one sentence explaining your verdict"}"""


class DirectnessJudge(BaseJudge):
    name = "directness"
    version = "v1"

    def evaluate(self, question, response, claude_client):
        user_msg = f"Question: {question}\n\nResponse:\n{response}"
        raw = claude_client.complete(SYSTEM_PROMPT, user_msg)
        parsed = self.parse_llm_json(raw)
        return self.make_result(parsed)
