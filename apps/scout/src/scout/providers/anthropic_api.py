"""The Anthropic provider.

The key is the user's, read from their environment, used from their machine.
scout never proxies a call through anything of ours and never writes the key
anywhere — which is the whole of what "bring your own model" has to mean to be
worth saying.
"""

import os

import anthropic

from ..errors import ScoutError

DEFAULT_MODEL = "claude-sonnet-5"

API_KEY_VARIABLE = "ANTHROPIC_API_KEY"

# The constraint, said to the model as well as enforced after it. The check in
# grounding.py is what actually holds the line — this is here so that the
# common case does not have to be caught by it.
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


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("SCOUT_MODEL", DEFAULT_MODEL)

    def tailor(self, *, master: str, posting: str) -> str:
        if not os.environ.get(API_KEY_VARIABLE):
            raise ScoutError(
                f"{API_KEY_VARIABLE} is not set.",
                detail=(
                    "scout uses your own Anthropic key and never stores it. "
                    f"Set it with: export {API_KEY_VARIABLE}=sk-ant-..."
                ),
            )

        client = anthropic.Anthropic()
        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=16000,
                system=SYSTEM,
                # Medium rather than the default: this is a rewrite of a
                # document that is already written, not a reasoning problem,
                # and effort is the first thing that shows up on the bill.
                output_config={"effort": "medium"},
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"<master_resume>\n{master}\n</master_resume>\n\n"
                            f"<posting>\n{posting}\n</posting>\n\n"
                            "Tailor the master resume to this posting."
                        ),
                    }
                ],
            )
        except anthropic.APIStatusError as exc:
            raise ScoutError(
                f"The model call failed: {exc.status_code} from Anthropic.",
                detail=str(getattr(exc, "message", exc)),
            ) from exc
        except anthropic.APIError as exc:
            raise ScoutError(f"The model call failed: {exc}") from exc

        if response.stop_reason == "refusal":
            raise ScoutError("The model call failed: the model declined this request.")

        draft = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()
        if not draft:
            raise ScoutError("The model call failed: it returned nothing.")
        return draft
