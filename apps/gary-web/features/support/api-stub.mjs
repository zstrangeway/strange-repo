import http from "node:http";

const PORT = 8799;

export const BASE_URL = `http://127.0.0.1:${PORT}`;

let server = null;
let body = { status: "ok", database: "ok" };

export function reports(status, database) {
  body = { status, database };
}

export async function start() {
  if (server) {
    return;
  }

  server = http.createServer((req, res) => {
    if (req.url === "/health") {
      // The page fetches this from the browser, so it is cross-origin —
      // matching gary-api, which allows any origin for /health.
      res.writeHead(200, {
        "content-type": "application/json",
        "access-control-allow-origin": "*",
      });
      res.end(JSON.stringify(body));
      return;
    }

    res.writeHead(404);
    res.end();
  });

  await new Promise((resolve) => server.listen(PORT, "127.0.0.1", resolve));
}

export async function stop() {
  if (!server) {
    return;
  }

  const closing = server;
  server = null;
  await new Promise((resolve) => closing.close(resolve));
}
