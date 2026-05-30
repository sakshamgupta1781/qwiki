import textwrap

LINE_WIDTH = 54


def format_output(articles, result):
    bar = "═" * LINE_WIDTH
    thin = "─" * LINE_WIDTH

    answer = result.get("answer", "")
    wrapped_answer = textwrap.fill(answer, width=LINE_WIDTH)

    source_items = result.get("sources", [])
    source_lines = "\n".join(f"• {s}" for s in source_items) if source_items else ""

    if source_items:
        source_titles = set()
        for s in source_items:
            t = s.split(" — ")[0].split(" - ")[0].strip()
            source_titles.add(t.lower())

        relevant = [a for a in articles
                    if a["title"].lower() in source_titles
                    or any(t in a["title"].lower() for t in source_titles)]
        url_lines = "\n".join(f"• {a['url']}" for a in relevant) if relevant else ""
    else:
        url_lines = "\n".join(f"• {a['url']}" for a in articles[:5])

    output = f"""
\U0001f4cc Answer
{thin}
{wrapped_answer}
"""

    if source_lines:
        output += f"""
\U0001f4cb Sources
{thin}
{source_lines}
"""

    if url_lines:
        output += f"""
\U0001f517 Links
{thin}
{url_lines}
"""

    return output


def format_refusal():
    return (
        "⚠️  This query has been blocked for safety reasons.\n"
        "qwiki-ask is designed for general knowledge questions.\n"
        "Please rephrase your question or try a different topic."
    )


def format_gibberish():
    return (
        "❓ I couldn't understand that input.\n"
        "Please ask a question in plain English."
    )


def format_no_results(question):
    return (
        f"No Wikipedia results found for: {question}\n"
        "Try rephrasing your question with different keywords."
    )


def format_no_answer():
    return (
        "I couldn't find enough information in Wikipedia to answer "
        "this question.\nTry asking something more specific."
    )
