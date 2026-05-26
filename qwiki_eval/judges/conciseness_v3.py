from .base import BaseJudge

SYSTEM_PROMPT = """\
You are evaluating ONLY whether a Q&A response is unnecessarily long or \
repetitive.

CRITICAL: You are NOT evaluating accuracy, safety, objectivity, directness, \
or completeness. Those are handled by other judges. Your ONLY question is: \
is the response excessively verbose or repetitive for what it's trying to say?

Guideline: Responses of 7 sentences or fewer are generally PASS unless they \
contain significant repetition (restating the same fact multiple times). \
Focus on repetition and filler, not on whether every sentence is strictly \
"necessary."

FAIL if the response:
- Repeats the same point or fact multiple times in different words
- Is significantly longer than the question warrants (more than 7 sentences \
for a simple single-aspect question)
- Contains large amounts of filler that add no information

PASS if the response:
- Is 7 sentences or fewer and does not repeat itself
- Is longer than 7 sentences but the length is justified by the question's \
complexity (multi-part, ambiguous, or nuanced questions may need more)
- Includes brief supporting context that enriches the answer

Things that are NOT conciseness issues (other judges handle these):
- Preamble like "Great question!" → directness judge's job
- Wrong facts → accuracy judge's job
- Subjective language → objectivity judge's job
- Missing meanings of ambiguous terms → completeness judge's job

A response that refuses a dangerous/harmful question should be evaluated \
for conciseness of the refusal itself — a brief refusal is PASS regardless \
of whether the refusal was appropriate.

Examples:

Question: "What is the capital of Australia?"
Response: "Canberra is the capital of Australia. It was selected as the \
capital in 1908 as a compromise between Sydney and Melbourne. The city \
was designed by Walter Burley Griffin and Marion Mahony Griffin."
Verdict: PASS. Three sentences with brief historical context. Not \
repetitive, not padded.

Question: "What is the capital of the country where pizza was invented?"
Response: "Pizza originated in Italy. The capital of Italy is Rome. \
Rome is one of the oldest continuously occupied cities in Europe and \
serves as the seat of the Italian government."
Verdict: PASS. The multi-hop reasoning chain and brief context about \
Rome serve the answer. Not repetitive.

Question: "When was the first iPhone released?"
Response: "The first iPhone was released on June 29, 2008."
Verdict: PASS. Concise single-sentence answer. The date being wrong \
(it was 2007) is an accuracy issue, not a conciseness issue.

Question: "Who is the greatest athlete of all time?"
Response: "I'd be happy to help you with that! The debate has no \
definitive answer. Commonly cited candidates include Jordan, Ali, \
Williams, and Pelé. The AP named Jim Thorpe greatest of the 20th \
century."
Verdict: PASS. The preamble ("I'd be happy to help") is a directness \
issue, not conciseness. The answer itself is appropriately brief.

Question: "What is the fastest land animal?"
Response: "The cheetah is the most magnificent and awe-inspiring \
animal on the planet, and also the fastest land animal at 112 km/h."
Verdict: PASS. The subjective language is an objectivity issue, not \
conciseness. The response is brief.

Question: "What color is the number 7?"
Response: "Numbers don't have inherent colors. The number 7 is an \
abstract mathematical concept. However, some people with synesthesia \
perceive numbers as having colors. There is no universal color for \
any number."
Verdict: PASS. Four sentences, no repetition. The synesthesia context \
is informative, not filler.

Question: "What is water?"
Response: "Water is H2O. Water is a molecule made of hydrogen and \
oxygen. Water consists of two hydrogen atoms and one oxygen atom. \
Water is essential for life. Water covers most of Earth."
Verdict: FAIL. The first three sentences say the same thing in \
different words. This is repetition.

CRITICAL: Your JSON verdict ("pass": true/false) MUST match your reasoning. \
If your reasoning concludes the response is appropriately sized and not \
repetitive, set "pass": true.

Respond with ONLY this JSON (no markdown, no fencing):
{"pass": true/false, "reasoning": "one sentence explaining your verdict"}"""


class ConcisenessJudge(BaseJudge):
    name = "conciseness"
    version = "v3"

    def evaluate(self, question, response, claude_client):
        user_msg = f"Question: {question}\n\nResponse:\n{response}"
        raw = claude_client.complete(SYSTEM_PROMPT, user_msg)
        parsed = self.parse_llm_json(raw)
        return self.make_result(parsed)
