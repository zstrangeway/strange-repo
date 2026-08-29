"""The instruction every provider sends, in one place.

Shared rather than copied because two providers with two slightly different
versions of this is the failure nobody notices: the drafts get subtly worse on
one of them and the grounding check absorbs the difference silently.

It is a request, not a guarantee. `grounding.py` is what holds when a model
ignores it — which is why this file can afford to be short.
"""

SYSTEM = """\
You are tailoring somebody's resume to one job posting.

You may reorder sections and bullets, cut what is irrelevant to this posting, \
and rephrase what is there to use the posting's own vocabulary.

You may not add anything. Do not introduce an employer, job title, skill, \
technology, qualification, date or metric that is not already in the master \
resume. If the posting asks for something the candidate does not have, leave \
it out — do not imply it, and do not hedge it into the text. Rephrasing must \
not strengthen a claim: "familiar with" does not become "expert in", and a \
number never grows.

Return the tailored resume as markdown and nothing else. No preamble, no \
explanation, no code fence."""


def request(master: str, posting: str) -> str:
    """The user turn. Tagged, so the two documents cannot bleed together."""
    return (
        f"<master_resume>\n{master}\n</master_resume>\n\n"
        f"<posting>\n{posting}\n</posting>\n\n"
        "Tailor the master resume to this posting."
    )
