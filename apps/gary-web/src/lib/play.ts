// Reading a turn as it happens.
//
// EventSource is not an option here, and it is worth saying why in the file
// that would otherwise be two lines long. gary's session is a bearer token in
// localStorage — deliberately, because a gary-api cookie would be third-party
// to gary-web and dropped by Safari and Firefox — and EventSource cannot set
// an Authorization header. So this is fetch, a ReadableStream and a small
// SSE parser.
//
// Everything after the first byte arrives as a frame rather than a status.
// Once gary-api has sent headers it cannot change its mind, so a refusal and
// a failure are both events on the open stream, and the caller renders them
// in the transcript rather than as a broken page.

import type { Roll } from "./api";
import { getLogger, REQUEST_ID_HEADER, requestId } from "./logger";
import { storedToken } from "./session";

const UNAVAILABLE = "gary is unavailable, try again shortly";

const log = getLogger("play");

// A roll on the stream and a roll in the transcript are the same thing, so
// they are the same type. Re-exported because this is where a caller reading
// the stream looks for it.
export type { Roll };

export type WorldChange = { kind: string } & Record<string, unknown>;

export type TurnEvent =
  | { type: "turn"; turn_id: string; role: string }
  | { type: "narration"; text: string }
  | { type: "roll"; roll: Roll }
  | { type: "world"; change: WorldChange }
  | { type: "scene"; scene_id: string; title: string }
  | { type: "done"; turn_id: string }
  | { type: "refusal"; detail: string }
  | { type: "error"; detail: string };

function baseUrl(): string {
  return process.env.NEXT_PUBLIC_GARY_API_URL ?? "http://127.0.0.1:8000";
}

/**
 * Split an SSE buffer into whole frames, returning what is left over.
 *
 * Kept separate because it is the part that is easy to get wrong and easy to
 * test: a chunk boundary lands wherever the network puts it, which is very
 * often in the middle of a frame and occasionally in the middle of a word.
 */
export function parseFrames(buffer: string): {
  events: TurnEvent[];
  rest: string;
} {
  const events: TurnEvent[] = [];

  // Cut at the last frame boundary rather than splitting and popping: what
  // follows it is either nothing or a frame still arriving, and either way it
  // is not this call's to read.
  const boundary = buffer.lastIndexOf("\n\n");
  if (boundary === -1) {
    return { events, rest: buffer };
  }

  const rest = buffer.slice(boundary + 2);

  for (const frame of buffer.slice(0, boundary).split("\n\n")) {
    let name = "";
    let data = "";

    for (const line of frame.split("\n")) {
      // Comment lines are keepalives and are not JSON. Passing one to
      // JSON.parse throws, which would end a turn that was fine.
      if (line.startsWith(":")) continue;
      if (line.startsWith("event:")) name = line.slice("event:".length).trim();
      if (line.startsWith("data:")) data += line.slice("data:".length).trim();
    }

    if (!name || !data) continue;

    let payload: Record<string, unknown>;
    try {
      payload = JSON.parse(data);
    } catch (error) {
      log.error("play.unreadable_frame", { event: name, error });
      continue;
    }

    events.push(asEvent(name, payload));
  }

  return { events: events.filter(Boolean) as TurnEvent[], rest };
}

function asEvent(name: string, payload: Record<string, unknown>): TurnEvent {
  switch (name) {
    case "turn":
      return {
        type: "turn",
        turn_id: String(payload.turn_id ?? ""),
        role: String(payload.role ?? ""),
      };
    case "narration":
      return { type: "narration", text: String(payload.text ?? "") };
    case "roll":
      return { type: "roll", roll: payload as unknown as Roll };
    case "world":
      return { type: "world", change: payload as unknown as WorldChange };
    case "scene":
      return {
        type: "scene",
        scene_id: String(payload.scene_id ?? ""),
        title: String(payload.title ?? ""),
      };
    case "done":
      return { type: "done", turn_id: String(payload.turn_id ?? "") };
    case "refusal":
      return { type: "refusal", detail: String(payload.detail ?? UNAVAILABLE) };
    default:
      // Anything gary-api adds later reads as an error rather than being
      // dropped in silence. A frame nobody renders is a turn that appears to
      // stop for no reason.
      return { type: "error", detail: String(payload.detail ?? UNAVAILABLE) };
  }
}

/**
 * Take a turn, calling back with each event as it arrives.
 *
 * Everything refusable outright — no session, not your campaign, nothing
 * said, nobody to play — comes back as a rejected status before any of this
 * runs, so those are returned rather than streamed.
 */
export async function takeTurn(
  campaignId: string,
  message: string,
  onEvent: (event: TurnEvent) => void,
  signal?: AbortSignal,
): Promise<{ ok: boolean; message?: string; code?: string }> {
  return stream(`/campaigns/${campaignId}/turns`, { message }, onEvent, signal);
}

/**
 * Have gary open the scene.
 *
 * The same frames as a turn, because it is one — the only difference is that
 * nobody said anything to prompt it. Refused with `already_begun` if the
 * campaign has started, which is what makes it safe to call on sight of an
 * empty transcript rather than having to be certain first.
 */
export async function beginCampaign(
  campaignId: string,
  onEvent: (event: TurnEvent) => void,
  signal?: AbortSignal,
): Promise<{ ok: boolean; message?: string; code?: string }> {
  return stream(`/campaigns/${campaignId}/opening`, undefined, onEvent, signal);
}

async function stream(
  path: string,
  body: unknown,
  onEvent: (event: TurnEvent) => void,
  signal?: AbortSignal,
): Promise<{ ok: boolean; message?: string; code?: string }> {
  const token = storedToken();
  const request_id = requestId();

  let response: Response;
  try {
    response = await fetch(`${baseUrl()}${path}`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        accept: "text/event-stream",
        ...(token ? { authorization: `Bearer ${token}` } : {}),
        [REQUEST_ID_HEADER]: request_id,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
      cache: "no-store",
    });
  } catch (error) {
    log.error("play.unreachable", { request_id, path, error });
    return { ok: false, message: UNAVAILABLE };
  }

  if (!response.ok) {
    let body: { detail?: unknown; code?: unknown } = {};
    try {
      body = (await response.json()) ?? {};
    } catch {
      body = {};
    }
    const said =
      typeof body.detail === "string" ? body.detail : UNAVAILABLE;
    return {
      ok: false,
      message: said,
      code: typeof body.code === "string" ? body.code : undefined,
    };
  }

  if (!response.body) {
    // A 200 with nothing to read. Not something gary-api does, but a proxy
    // that buffered the whole response away would look exactly like this.
    log.error("play.no_body", { request_id, path });
    return { ok: false, message: UNAVAILABLE };
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;

      // stream: true, because a multi-byte character can straddle a chunk
      // boundary and decoding it in halves produces a replacement character
      // in the middle of a word.
      buffer += decoder.decode(value, { stream: true });

      const { events, rest } = parseFrames(buffer);
      buffer = rest;
      for (const event of events) onEvent(event);
    }
  } catch (error) {
    // Includes the abort that unmounting causes, which is not worth
    // reporting to anyone: the page it would have rendered into is gone.
    if (!signal?.aborted) {
      log.error("play.interrupted", { request_id, path, error });
      onEvent({ type: "error", detail: UNAVAILABLE });
    }
  } finally {
    reader.releaseLock();
  }

  return { ok: true };
}
