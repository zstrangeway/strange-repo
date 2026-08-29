"""A job board, on localhost.

Four of them, really: one that serves a posting, one that serves the shell of
a page and fills it in with JavaScript, one that refuses, and one that never
answers. They are real HTTP on a real socket, because the thing being tested
is what trafilatura and httpx do with a real response.
"""

import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

POSTING_PAGE = """<!doctype html>
<html><head><title>{title} at {company}</title></head>
<body>
  <nav><a href="/">Jobs</a> <a href="/about">About Bilgewater Boards</a></nav>
  <article>
    <h1>{title}</h1>
    <h2>{company}</h2>
    <p>We are looking for someone with deep Postgres and Python experience to
    own the platform our whole engineering organisation deploys through. You
    would be the third engineer on the team and the first one focused on the
    build and release path end to end.</p>
    <p>The work is a mix of reliability and developer experience: making the
    deploy pipeline fast enough that nobody batches their changes up, keeping
    the Terraform that describes our infrastructure honest, and being the
    person who understands why the database is slow this week.</p>
    <p>We would like someone who has done this before at a company where the
    answer was not simply to buy something. Experience running Postgres in
    production matters more to us than any particular cloud.</p>
  </article>
  <footer>Bilgewater Boards, all rights reserved.</footer>
</body></html>"""

# A board's index: every job it has, as links. Long enough to pass the length
# check — the real Greenhouse one extracts to 3.2k characters — and with
# almost no prose in it, which is what actually tells the two apart.
INDEX_PAGE = """<!doctype html>
<html><head><title>Jobs at Wilding Labs</title></head>
<body>
  <nav><a href="/">Jobs</a></nav>
  <main>
    <h1>Open roles</h1>
    <p>Level up your career by having opportunities sent to your inbox.</p>
    <ul>
      <li><a href="/jobs/1">Staff Engineer — London, UK</a></li>
      <li><a href="/jobs/2">Senior Platform Engineer — Remote</a></li>
      <li><a href="/jobs/3">Platform Lead — New York, USA</a></li>
      <li><a href="/jobs/4">Infrastructure Engineer — Berlin, Germany</a></li>
      <li><a href="/jobs/5">Site Reliability Engineer — Remote</a></li>
      <li><a href="/jobs/6">Data Platform Engineer — London, UK</a></li>
      <li><a href="/jobs/7">Security Engineer — Remote</a></li>
      <li><a href="/jobs/8">Engineering Manager, Platform — London, UK</a></li>
      <li><a href="/jobs/9">Developer Experience Engineer — Remote</a></li>
      <li><a href="/jobs/10">Database Reliability Engineer — Berlin, Germany</a></li>
      <li><a href="/jobs/11">Staff Software Engineer, Billing — Remote</a></li>
      <li><a href="/jobs/12">Principal Engineer, Infrastructure — London, UK</a></li>
    </ul>
  </main>
</body></html>"""

# What a board that renders in the browser serves to anything that is not a
# browser. There is no posting in it at any length.
SHELL_PAGE = """<!doctype html>
<html><head><title>Loading…</title></head>
<body><div id="root"></div><script src="/app.js"></script></body></html>"""


class JobBoard:
    """An HTTP server that behaves however a scenario needs it to."""

    def __init__(self, mode: str, *, title: str = "", company: str = "") -> None:
        self.mode = mode
        self.title = title
        self.company = company
        board = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if board.mode == "refuses":
                    self.send_error(403, "Forbidden")
                    return
                if board.mode == "silent":
                    # Longer than SCOUT_FETCH_TIMEOUT, so the client gives up
                    # first and the scenario sees a timeout rather than a body.
                    time.sleep(5)
                    return
                if board.mode == "shell":
                    body = SHELL_PAGE
                elif board.mode == "index":
                    body = INDEX_PAGE
                else:
                    body = POSTING_PAGE.format(title=board.title, company=board.company)
                encoded = body.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, *args):
                """Quiet. behave's output is the thing worth reading."""

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}/jobs/1"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
