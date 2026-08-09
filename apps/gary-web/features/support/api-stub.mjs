import http from "node:http";

const PORT = 8799;

export const BASE_URL = `http://127.0.0.1:${PORT}`;

let server = null;

export async function start() {
  if (server) {
    return;
  }

  server = http.createServer((req, res) => {
    if (req.url === "/health") {
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify({ status: "ok" }));
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
