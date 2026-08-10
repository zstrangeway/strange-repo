"""The fake provider's consent screen.

Only mounted when IDENTITY_FAKE is on. A real provider shows a page, and
that page is a real browser navigation away from gary — so the double has to
be one too, or the end-to-end specs exercise everything except the half most
likely to be wrong.

It asks who you are rather than deciding for you, which is what makes a
scenario able to say "sign in as Ada" and mean it.
"""

from fastapi import APIRouter, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse

from gary_api import identity
from gary_api.identity.fake import FAKE_HINT

router = APIRouter(prefix="/auth/fake", tags=["fake"])

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{label}</title></head>
<body>
  <h1>{label}</h1>
  <p>This is not {label}. It is gary's stand-in for it.</p>
  <form method="post">
    <label for="code">Who are you?</label>
    <input id="code" name="code" value="{hint}" size="60"
           data-testid="fake-identity">
    <button type="submit" data-testid="fake-continue">Continue</button>
  </form>
</body></html>"""


def _guard() -> None:
    if not identity.faking():
        # Not merely hidden: a deployment with real providers must not carry
        # a way to assert any identity it likes.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")


@router.get("/{provider}/authorize", response_class=HTMLResponse)
async def consent_page(provider: str) -> HTMLResponse:
    _guard()
    return HTMLResponse(PAGE.format(label=provider.title(), hint=FAKE_HINT))


@router.post("/{provider}/authorize")
async def agree(
    provider: str, redirect_uri: str, code: str = Form(...), state: str = ""
) -> RedirectResponse:
    _guard()
    separator = "&" if "?" in redirect_uri else "?"
    target = f"{redirect_uri}{separator}code={code}&state={state or provider}"
    # 303 so the browser follows with GET rather than repeating the POST.
    return RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)
