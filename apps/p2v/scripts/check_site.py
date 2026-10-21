"""Check local HTML and CSS references without third-party dependencies."""

from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1] / "dist"
errors = []
checked = 0


def check_reference(source, reference):
    global checked
    url = urlsplit(reference)
    if url.scheme or url.netloc or not url.path:
        return
    base = ROOT if url.path.startswith("/") else source.parent
    target = (base / unquote(url.path).lstrip("/")).resolve()
    if target.is_dir():
        target /= "index.html"
    checked += 1
    if not target.is_relative_to(ROOT) or not target.is_file():
        errors.append(f"{source.relative_to(ROOT)}: missing local target {reference}")


class References(HTMLParser):
    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in {"src", "href", "poster", "action"} and value:
                check_reference(self.source, value)


pages = sorted(ROOT.glob("*.html"))
if not (ROOT / "index.html").is_file():
    errors.append("Missing dist/index.html")
for page in pages:
    parser = References()
    parser.source = page
    parser.feed(page.read_text())
    parser.close()
for stylesheet in ROOT.rglob("*.css"):
    for reference in re.findall(r"url\(\s*['\"]?([^)'\"\s]+)['\"]?\s*\)", stylesheet.read_text()):
        check_reference(stylesheet, reference)
if errors:
    raise SystemExit("\n".join(errors))
print(f"p2v: checked {len(pages)} HTML pages and {checked} local page/asset references")
