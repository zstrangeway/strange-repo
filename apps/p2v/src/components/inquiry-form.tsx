"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Button } from "@gary/ui/components/button";
import { Input } from "@gary/ui/components/input";
import { Label } from "@gary/ui/components/label";
import { Textarea } from "@gary/ui/components/textarea";

const interests = [
  "Training",
  "Camps",
  "14U Team",
  "16U Team",
  "Tryouts",
  "Schedule",
  "Something else",
];

export function InquiryForm() {
  const [interest, setInterest] = useState("Training");
  const [message, setMessage] = useState<{ body: string; href: string } | null>(
    null,
  );
  const [copyStatus, setCopyStatus] = useState("");
  const preview = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const requested = new URLSearchParams(location.search).get("interest");
    if (requested && interests.includes(requested)) setInterest(requested);
  }, []);

  useEffect(() => {
    if (!message) return;
    preview.current?.focus({ preventScroll: true });
    preview.current?.scrollIntoView({
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
      block: "nearest",
    });
  }, [message]);

  function review(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const value = (key: string) => String(data.get(key) || "").trim();
    const athleteDetails = [
      value("athlete") ? `Athlete: ${value("athlete")}` : "",
      value("age") ? `Age: ${value("age")}` : "",
    ]
      .filter(Boolean)
      .join("\n");
    const body = [
      "Hi Coach Will,",
      `I’m interested in ${value("interest")}.`,
      `Name: ${value("name")}\nReply email: ${value("email")}`,
      athleteDetails,
      value("message"),
      `Thanks,\n${value("name")}`,
    ]
      .filter(Boolean)
      .join("\n\n");
    setMessage({
      body,
      href: `mailto:p2vacademy@gmail.com?subject=${encodeURIComponent("P2V inquiry: " + value("interest"))}&body=${encodeURIComponent(body)}`,
    });
    setCopyStatus("");
  }

  async function copyMessage() {
    try {
      await navigator.clipboard.writeText(message!.body);
      setCopyStatus("Message copied.");
    } catch {
      setCopyStatus("Select the message above to copy it manually.");
    }
  }

  return (
    <form id="inquiry" onSubmit={review} onChange={() => setMessage(null)}>
      <div className="field-row">
        <Label htmlFor="inquiry-name">
          Your name
          <Input
            id="inquiry-name"
            name="name"
            autoComplete="name"
            required
            maxLength={100}
            placeholder="Parent or guardian name"
          />
        </Label>
        <Label htmlFor="inquiry-email">
          Your email
          <Input
            id="inquiry-email"
            type="email"
            name="email"
            autoComplete="email"
            required
            maxLength={200}
            placeholder="you@example.com"
          />
        </Label>
      </div>
      <div className="field-row">
        <Label htmlFor="inquiry-athlete">
          Athlete’s first name <span className="optional">(optional)</span>
          <Input
            id="inquiry-athlete"
            name="athlete"
            maxLength={100}
            placeholder="First name"
          />
        </Label>
        <Label htmlFor="inquiry-age">
          Athlete’s age <span className="optional">(optional)</span>
          <Input
            id="inquiry-age"
            type="number"
            name="age"
            min={1}
            max={99}
            placeholder="Age"
          />
        </Label>
      </div>
      <Label htmlFor="inquiry-interest">
        I’m interested in
        <select
          id="inquiry-interest"
          name="interest"
          value={interest}
          onChange={(event) => setInterest(event.target.value)}
        >
          {interests.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
      </Label>
      <Label htmlFor="inquiry-message">
        How can we help?
        <Textarea
          id="inquiry-message"
          name="message"
          rows={4}
          maxLength={2000}
          placeholder="Experience, goals, availability, or any questions…"
          required
        />
      </Label>
      <Button className="button dark" type="submit">
        Review my message
      </Button>
      <p className="form-caption">
        You’ll send the email from your own email app.
      </p>
      <div
        id="email-preview"
        ref={preview}
        hidden={!message}
        tabIndex={-1}
        aria-labelledby="email-preview-title"
      >
        <h3 id="email-preview-title">Review your message.</h3>
        <p>
          Everything look right? Open your email app to send it to P2V, or edit
          the form and review it again.
        </p>
        <pre id="email-body">{message?.body}</pre>
        <div className="actions">
          <Button asChild className="button dark">
            <a id="email-link" href={message?.href}>
              Open email app
            </a>
          </Button>
          <Button
            type="button"
            id="copy-email"
            className="copy-button"
            onClick={copyMessage}
          >
            Copy message
          </Button>
        </div>
        <p id="copy-status" role="status">
          {copyStatus}
        </p>
      </div>
    </form>
  );
}
