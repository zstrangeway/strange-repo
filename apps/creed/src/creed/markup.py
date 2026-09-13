"""Turning the export's HTML into something a model can read.

Every ``description`` field in the export is HTML, and it is not the handful
of tags a glance suggests. Counting the abilities table alone: 807 spans, 580
table tags, 209 list tags, 257 line breaks, plus links, images, and a
nonstandard ``<ky>``. Real tables and real nested lists are exactly what a
hand-rolled stripper turns into one long run-on sentence, which is why this
goes through markdownify rather than a regular expression.

One thing markdownify does not do on its own: Wahapedia wraps rules keywords
in ``<span class="kwb">`` and stock conversion flattens them. The emphasis is
load-bearing — the rules mean something by TYRANIDS that they do not mean by
the word "tyranids" — so the converter below keeps it.
"""

from markdownify import MarkdownConverter

# The classes Wahapedia uses for keyword emphasis all begin "kw" (kwb, kwb2,
# and so on). Matching the prefix rather than the exact list means a new
# variant reads as a keyword instead of silently losing its emphasis.
_KEYWORD_CLASS_PREFIX = "kw"
_VERSION_CLASS = "h_number"


class _WahapediaConverter(MarkdownConverter):
    """markdownify, plus the one thing the export needs it to know."""

    def convert_span(self, el, text, parent_tags=None):
        classes = el.get("class") or []
        if any(name.startswith(_KEYWORD_CLASS_PREFIX) for name in classes):
            return f"**{text}**"
        # Wahapedia's rules-version marker sits inside the ability's name with
        # no separator, so it reads as "DEEP STRIKE24.09". It is worth keeping
        # — it says which rules commentary the text is from — but not worth
        # welding to the name.
        if _VERSION_CLASS in classes:
            return f" ({text})"
        return text

    # Wahapedia lays rules text out in divs, and markdownify has no rule for
    # a div, so its text passes through with nothing between it and the next
    # block. That welds an ability's name onto its version marker onto its
    # first sentence — "DEEP STRIKE24.09There are many ways...". Treating a
    # div as the block element it is puts the breaks back.
    def convert_div(self, el, text, parent_tags=None):
        text = (text or "").strip()
        return f"\n\n{text}\n\n" if text else ""

    # <ky> is Wahapedia's own tag and means the same thing as a kwb span.
    # BeautifulSoup parses it as an unknown element and markdownify passes its
    # text through, so without this the keyword loses its emphasis.
    def convert_ky(self, el, text, parent_tags=None):
        return f"**{text}**"


# Images in rules text are icons — a dice symbol, a phase marker. Their alt
# text is empty or decorative, so they add nothing to a model's reading of the
# rule and cost tokens to carry.
_converter = _WahapediaConverter(strip=["img"])


def to_markdown(html: str | None) -> str:
    """Convert one export description field to markdown.

    Empty and missing fields are common in the export — an ability row with no
    description, a datasheet with no damaged profile — so they come back as
    the empty string rather than raising.
    """
    if not html:
        return ""
    return _converter.convert(html).strip()
