"use client";

import { useRef, useState, type KeyboardEvent } from "react";
import { Button } from "@gary/ui/components/button";

const focuses = [
  {
    id: "skills",
    label: "Basketball skills",
    number: "01",
    title: "Make the next rep matter.",
    copy: "Work on your basketball skills with coaching that challenges you to learn, practice, and improve.",
  },
  {
    id: "athletic",
    label: "Strength & speed",
    number: "02",
    title: "Build the athlete behind the game.",
    copy: "Combine basketball skill work with strength and speed training to support your development as an athlete.",
  },
  {
    id: "mindset",
    label: "Mindset & character",
    number: "03",
    title: "Grow beyond the court.",
    copy: "Learn to respond to challenges, stay focused, and support your teammates. Mental toughness and character are part of the work.",
  },
];

export function TrainingTabs() {
  const [selected, setSelected] = useState(0);
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const focus = focuses[selected];

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let next: number;
    switch (event.key) {
      case "ArrowRight":
        next = (index + 1) % focuses.length;
        break;
      case "ArrowLeft":
        next = (index + focuses.length - 1) % focuses.length;
        break;
      case "Home":
        next = 0;
        break;
      case "End":
        next = focuses.length - 1;
        break;
      default:
        return;
    }
    event.preventDefault();
    setSelected(next);
    tabs.current[next]?.focus();
  }

  return (
    <>
      <div className="training-tabs" role="tablist" aria-label="Training focus">
        {focuses.map((item, index) => (
          <Button
            key={item.id}
            ref={(element) => {
              tabs.current[index] = element;
            }}
            type="button"
            role="tab"
            aria-selected={selected === index}
            aria-controls="focus-panel"
            id={`focus-${item.id}`}
            tabIndex={selected === index ? 0 : -1}
            onClick={() => setSelected(index)}
            onKeyDown={(event) => onKeyDown(event, index)}
          >
            {item.label}
          </Button>
        ))}
      </div>
      <div
        className="focus-panel"
        id="focus-panel"
        role="tabpanel"
        tabIndex={0}
        aria-labelledby={`focus-${focus.id}`}
      >
        <span className="focus-number" aria-hidden="true">
          {focus.number}
        </span>
        <div>
          <h3>{focus.title}</h3>
          <p>{focus.copy}</p>
          <a className="textlink" href="/contact.html?interest=Training">
            Ask about training
          </a>
        </div>
      </div>
    </>
  );
}
