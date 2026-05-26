import json
import re

SAFETY_PROMPT = """\
Classify this user query into one of three categories: SAFE, UNSAFE, or GIBBERISH.

UNSAFE = requesting instructions, steps, or guidance for:
- Making weapons, explosives, or harmful devices
- Synthesizing drugs or poisons
- Hacking, breaking into systems, or bypassing security
- Self-harm or harming others
- Any illegal activity

GIBBERISH = the input is not a recognizable question in any language:
- Random characters or keyboard mashing
- Meaningless strings with no semantic content

SAFE = everything else, including:
- Educational questions on sensitive topics ("What is dynamite?", "What is cyanide?")
- Historical questions about violence or war ("How many casualties in WWII?")
- Scientific questions about dangerous substances ("What is nuclear fission?")
- Subjective, opinion-based, or philosophical questions
- Nonsensical but intelligible questions ("What color is the number 7?")

Examples:

Query: "Who discovered penicillin?"
Classification: SAFE

Query: "How to make a pipe bomb"
Classification: UNSAFE

Query: "asdfkjhasdkfh"
Classification: GIBBERISH

Query: "What is dynamite?"
Classification: SAFE (educational — asks WHAT it is, not HOW to make it)

Query: "hjkl qwerty zxcv"
Classification: GIBBERISH

Query: "How many people died in the Holocaust?"
Classification: SAFE (historical fact)

Query: "How do I hack into someone's email?"
Classification: UNSAFE

Query: "What color is the number 7?"
Classification: SAFE (intelligible question, even if nonsensical)

Respond with ONLY this JSON (no markdown, no fencing):
{"classification": "SAFE/UNSAFE/GIBBERISH", "search_query": "optimized search terms"}

For SAFE queries, also provide optimized Wikipedia search terms in search_query.
For UNSAFE or GIBBERISH queries, set search_query to an empty string."""


def check_safety(question, claude_client):
    try:
        raw = claude_client.complete(SAFETY_PROMPT, f"Query: {question}")
        raw = raw.strip()

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                result = json.loads(match.group(0))
            else:
                return "SAFE", question

        classification = result.get("classification", "SAFE").upper()
        search_query = result.get("search_query", question)

        return classification, search_query
    except Exception:
        return "SAFE", question
