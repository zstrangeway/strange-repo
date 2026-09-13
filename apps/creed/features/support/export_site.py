"""A stand-in for Wahapedia, with the conditional-GET behaviour that matters.

A stub that always returns 200 would let every freshness scenario pass while
the thing they are about — paying only for what changed — quietly did not
work. So this serves real ETags and real Last-Modified headers and answers 304
when the client sends a matching validator, which is what the origin does.

It can also be told to break: to stop answering at all (offline), to fail
partway through a sync, or to send a table whose columns have moved.
"""

import hashlib
import http.server
import threading
from email.utils import formatdate

from . import fixture


class ExportSite:
    """A local HTTP server serving one version of the export."""

    def __init__(self) -> None:
        self.tables = fixture.build()
        self.offline = False
        # Table name -> how many more requests to answer before failing, or a
        # replacement body to send instead.
        self.fail_after: int | None = None
        self.broken_table: str | None = None
        self.requests: list[str] = []
        self._served = 0
        self._modified = formatdate(usegmt=True)
        site = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                return

            def do_GET(self):  # the name http.server requires
                name = self.path.strip("/").removesuffix(".csv")
                site.requests.append(name)
                if site.offline:
                    self.send_error(503)
                    return
                if name not in site.tables:
                    self.send_error(404)
                    return
                if (
                    site.fail_after is not None
                    and name != "Last_update"
                    and site._served >= site.fail_after
                ):
                    self.send_error(500)
                    return
                if name != "Last_update":
                    site._served += 1
                body = site.tables[name]
                if name == site.broken_table:
                    body = body.replace("|", "~", 1)
                    body = "﻿wrong|columns|\nx|y|\n"
                payload = body.encode("utf-8")
                etag = '"' + hashlib.sha1(payload).hexdigest()[:16] + '"'
                if self.headers.get("If-None-Match") == etag:
                    self.send_response(304)
                    self.send_header("ETag", etag)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/csv")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("ETag", etag)
                self.send_header("Last-Modified", site._modified)
                self.end_headers()
                self.wfile.write(payload)

        self._server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def set_last_update(self, stamp: str) -> None:
        self.tables["Last_update"] = fixture.table(["last_update"], [(stamp,)])

    def change_price(self, datasheet_id: str, old: str, new: str) -> None:
        """Move a price, the way a dataslate does."""
        table = self.tables["Datasheets_models_cost"]
        self.tables["Datasheets_models_cost"] = table.replace(
            f"{datasheet_id}|2|5 models|{old}|", f"{datasheet_id}|2|5 models|{new}|"
        )

    def drop_datasheet(self, datasheet_id: str) -> None:
        lines = self.tables["Datasheets"].split("\n")
        self.tables["Datasheets"] = "\n".join(
            line for line in lines if not line.startswith(f"{datasheet_id}|")
        )

    def downloads(self) -> list[str]:
        return [name for name in self.requests if name != "Last_update"]

    def reset_requests(self) -> None:
        self.requests = []

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
