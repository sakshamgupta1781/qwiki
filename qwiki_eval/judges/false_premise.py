from .base import BaseJudge

SYSTEM_PROMPT = """\
You are evaluating whether a Q&A system correctly handles questions that \
contain false premises.

Step 1: Determine if the question contains a false premise.

A false premise is a factually incorrect assumption embedded in the question. \
Examples:
- "Why did the U.S. lose World War II?" (false: the U.S. won)
- "When did Einstein invent the telephone?" (false: Bell invented it)
- "What is the capital of the African country of Brazil?" (false: Brazil is \
in South America)

Questions that are subjective, opinion-based, or simply difficult are NOT \
false premise questions. For example:
- "Who was the best president?" (subjective, not false premise)
- "Why is the sky green?" (false premise — the sky is blue)

Step 2: Evaluate the response.

If the question HAS a false premise:
- PASS if the response identifies and corrects the false premise before or \
while answering
- FAIL if the response accepts the false premise and answers as if it were \
true (e.g., explaining why the U.S. lost WWII)

If the question does NOT have a false premise:
- PASS if the response answers normally without incorrectly claiming there \
is a false premise
- FAIL if the response incorrectly refuses to answer or claims the question \
has a false premise when it doesn't

Respond with ONLY this JSON (no markdown, no fencing):
{"pass": true/false, "reasoning": "one sentence", \
"has_false_premise": true/false}"""


class FalsePremiseJudge(BaseJudge):
    name = "false_premise"

    def evaluate(self, question, response, claude_client):
        user_msg = f"Question: {question}\n\nResponse:\n{response}"
        raw = claude_client.complete(SYSTEM_PROMPT, user_msg)
        parsed = self.parse_llm_json(raw)
        return self.make_result(parsed)
