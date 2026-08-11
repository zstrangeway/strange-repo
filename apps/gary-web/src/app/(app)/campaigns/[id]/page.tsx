"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useRef, useState } from "react";

import { Badge } from "@gary/ui/components/badge";
import { Button } from "@gary/ui/components/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@gary/ui/components/card";
import { Skeleton } from "@gary/ui/components/skeleton";

import type { Campaign, Model, Scene, World } from "@/lib/api";
import {
  beginScene,
  campaign as readCampaign,
  partyOf,
  runnableModels,
  scenesOf,
  transcript as readTranscript,
  changeModel,
  worldOf,
} from "@/lib/gary";
import { beginCampaign, takeTurn, type TurnEvent } from "@/lib/play";
import { useSession } from "@/lib/use-session";
import { useRouter } from "next/navigation";

import { Notice } from "../../../form-parts";
import Composer from "./composer";
import ModelPicker from "./model-picker";
import Party from "./party-card";
import SceneBreak from "./scene-break";
import Transcript, { type Entry } from "./transcript";

// The table.
//
// Everything mechanical happens at gary-api: this asks, renders what comes
// back, and never decides anything itself. The one piece of real logic here
// is folding a stream of frames into the transcript as they arrive, and it is
// deliberately small — the parsing that makes it possible lives in
// `src/lib/play.ts`, where the coverage gate can see it.
export default function CampaignPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { user } = useSession();
  const router = useRouter();

  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [missing, setMissing] = useState(false);
  const [models, setModels] = useState<Model[]>([]);
  const [world, setWorld] = useState<World | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [busy, setBusy] = useState(false);
  // Set the moment an opening is asked for, and never unset. A ref rather
  // than state because two renders can both see "nothing said yet" before
  // either sets it, and the point is to ask exactly once.
  const opening = useRef(false);
  const [trouble, setTrouble] = useState<string | undefined>(undefined);

  // Which entry the frames arriving now belong to. A ref rather than state:
  // several frames land between renders, and reading it from a closure over a
  // stale render would append the second half of a turn to the first.
  const answering = useRef<string | null>(null);

  // Which scene the turns arriving now belong to. A ref for the same reason:
  // the stream can open a new scene between renders, and a turn filed under
  // the scene a stale render knew about would render in the wrong place.
  const playing = useRef<string>("");

  // Projected by gary-api and never assembled here, so it is derived rather
  // than held: a second copy of the party is a second thing to be wrong.
  const party = world?.party ?? [];

  const loadWorld = useCallback(async () => {
    setWorld(await worldOf(id));
  }, [id]);

  const loadScenes = useCallback(async () => {
    const found = await scenesOf(id);
    setScenes(found);
    const open = found.find((scene) => scene.open) ?? found.at(-1);
    if (open) {
      playing.current = open.id;
    }
    return found;
  }, [id]);

  const load = useCallback(async () => {
    const found = await readCampaign(id);
    if (!found) {
      setMissing(true);
      return;
    }

    // A campaign nobody has built a party for has nothing to show here, and
    // no way to get one from this page any more. Sent back to the step that
    // does rather than left on a table it cannot lay.
    const here = await partyOf(id);
    if (!here.some((character) => character.played_by === "player")) {
      router.replace(`/campaigns/${id}/party`);
      return;
    }

    const [runnable, said] = await Promise.all([
      runnableModels(),
      readTranscript(id),
      loadScenes(),
    ]);

    setCampaign(found);
    setModels(runnable);
    setEntries(
      said.map((turn) => ({
        id: turn.id,
        role: turn.role,
        text: turn.content,
        rolls: turn.rolls ?? [],
        complete: turn.complete,
        sceneId: turn.scene_id,
      })),
    );
    await loadWorld();
  }, [id, router, loadWorld, loadScenes]);

  useEffect(() => {
    // Fetching on mount, which is what an effect is for.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  /** One frame from the open stream, folded into what is on screen. */
  function fold(event: TurnEvent) {
    if (event.type === "turn") {
      answering.current = event.turn_id;
      setEntries((held) => [
        ...held,
        {
          id: event.turn_id,
          role: "gm",
          text: "",
          rolls: [],
          complete: false,
          sceneId: playing.current,
        },
      ]);
      return;
    }

    if (event.type === "narration" || event.type === "roll") {
      const at = answering.current;
      setEntries((held) =>
        held.map((entry) =>
          entry.id !== at
            ? entry
            : event.type === "narration"
              ? { ...entry, text: entry.text + event.text }
              : { ...entry, rolls: [...entry.rolls, event.roll] },
        ),
      );
      return;
    }

    if (event.type === "done") {
      setEntries((held) =>
        held.map((entry) =>
          entry.id === event.turn_id ? { ...entry, complete: true } : entry,
        ),
      );
      return;
    }

    if (event.type === "scene") {
      // gary asked for a break and the engine granted it once the turn was
      // over. Everything said from here belongs to the scene it opened.
      playing.current = event.scene_id;
      void loadScenes();
      return;
    }

    if (event.type === "world") {
      // What changed is already on the stream; asking for the world again is
      // how the party on screen agrees with the party gary is narrating
      // about, rather than this page re-implementing the projection.
      void loadWorld();
      return;
    }

    // Refused or broken. Both arrive as frames rather than statuses — the
    // status line was spent the moment the stream opened — and both leave
    // what has been narrated so far exactly where it is.
    //
    // Nothing is removed here, because not every error ends the turn: a tool
    // gary asked for and the engines refused arrives this way too, and gary
    // carries on narrating around it. Tidying up an answer that never began
    // happens once the stream is over, where it can be told apart.
    setTrouble(
      event.type === "refusal"
        ? `gary declined: ${event.detail}`
        : `gary had a problem: ${event.detail}`,
    );
  }

  /** Drive one stream to the end and tidy up after it, whichever kind. */
  async function run(open: (onEvent: (event: TurnEvent) => void) => Promise<{
    ok: boolean;
    message?: string;
  }>) {
    const result = await open(fold);
    if (!result.ok) {
      setTrouble(result.message);
    }

    // An answer that opened and then said nothing at all — gary declining, or
    // gary being unreachable. gary-api has already deleted its turn, so
    // leaving the placeholder would show a turn that does not exist and would
    // still say "thinking" after everything had stopped.
    setEntries((held) =>
      held.filter(
        (entry) =>
          entry.role !== "gm" ||
          entry.complete ||
          entry.text !== "" ||
          entry.rolls.length > 0,
      ),
    );

    setBusy(false);
    // Both, and after the turn rather than during it: the engine may have
    // broken a long scene before this turn even joined one, and the page has
    // no other way to learn that happened.
    await Promise.all([loadWorld(), loadScenes()]);
  }

  async function say(message: string) {
    setTrouble(undefined);
    setBusy(true);
    answering.current = null;

    // Shown before the stream opens, because it is already true: gary-api
    // stores the player's turn before it answers.
    setEntries((held) => [
      ...held,
      {
        id: `said-${Date.now()}`,
        role: "player",
        text: message,
        rolls: [],
        complete: true,
        sceneId: playing.current,
      },
    ]);

    await run((onEvent) => takeTurn(id, message, onEvent));
  }

  // A table where everyone has sat down and nobody has spoken. Somebody has
  // to go first and it is not the player, so gary opens as soon as there is
  // anybody to open for — no button, because having made a character, being
  // asked to also press start is the same emptiness in a smaller box.
  //
  // Safe to fire on sight: gary-api refuses a second opening outright, so a
  // reload or another tab cannot produce two or spend twice.
  useEffect(() => {
    if (opening.current || !campaign || campaign.begun) {
      return;
    }
    if (party.length === 0 || entries.length > 0) {
      return;
    }

    opening.current = true;
    // Starting the turn is the point, and a turn starts by saying so.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTrouble(undefined);
    setBusy(true);
    answering.current = null;
    void run((onEvent) => beginCampaign(id, onEvent));
  });

  if (missing) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-3xl font-semibold tracking-tight">No such campaign</h1>
        <p className="text-sm text-muted-foreground">
          It may have been someone else&apos;s, or it may never have existed.
        </p>
        <div>
          <Button asChild variant="secondary">
            <Link href="/">Back to your campaigns</Link>
          </Button>
        </div>
      </div>
    );
  }

  if (!campaign) {
    return <Skeleton className="h-64 w-full" data-testid="campaign-loading" />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-semibold tracking-tight">
            {campaign.name}
          </h1>
          <p className="text-sm text-muted-foreground">
            {campaign.title}
            {world?.place ? ` · ${world.place}` : ""}
            {world && world.minutes > 0 ? ` · ${world.minutes} minutes in` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline">{campaign.system}</Badge>
          <ModelPicker
            models={models}
            current={campaign.model}
            chosen={campaign.model_chosen}
            onPick={async (model) => {
              const result = await changeModel(id, model);
              if (result.campaign) {
                setCampaign(result.campaign);
                return;
              }
              setTrouble(result.error);
            }}
          />
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <Card>
          <CardHeader>
            <CardTitle>The story so far</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-6">
            {/* What the adventure is about, until gary has said it better.
                It is here to cover the seconds the opening takes to arrive;
                once the opening has arrived the two say the same thing one
                after the other, and the second one is worse prose. */}
            {entries.length === 0 ? (
            <div
              className="rounded-lg border border-dashed p-4"
              data-testid="premise"
            >
              <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                {campaign.title}
              </p>
              <p className="mt-1 text-sm">{campaign.premise}</p>
              <p className="mt-2 text-sm" data-testid="hook">
                {campaign.hook}
              </p>
            </div>
            ) : null}

            <Transcript
              entries={entries}
              scenes={scenes}
              who={user?.display_name ?? "You"}
            />
            <Notice error={trouble} />
            <Composer
              busy={busy}
              disabled={world === null || party.length === 0}
              hint={
                world === null
                  ? "Finding the table…"
                  : party.length === 0
                    ? "Add somebody to the party first"
                    : undefined
              }
              onSay={say}
            />
            <SceneBreak
              disabled={busy || party.length === 0}
              onBreak={async (title) => {
                const result = await beginScene(id, title);
                if (result.scene) {
                  playing.current = result.scene.id;
                  await Promise.all([loadScenes(), loadWorld()]);
                  return;
                }
                setTrouble(result.error);
              }}
            />
          </CardContent>
        </Card>

        <Party campaignId={id} party={party} loading={world === null} />
      </div>
    </div>
  );
}
