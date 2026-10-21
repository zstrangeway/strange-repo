"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { Button } from "@gary/ui/components/button";

const links = [
  ["training", "Training"],
  ["teams", "Teams"],
  ["facility", "Facility"],
  ["about", "Our Story"],
  ["schedule", "Schedule"],
  ["contact", "Get Started"],
];

export function SiteHeader() {
  const pathname = usePathname();
  const page = pathname.replace(/\.html$/, "").replace(/\/$/, "");
  const [open, setOpen] = useState(false);
  const menu = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const desktop = matchMedia("(min-width: 1041px)");
    const closeOnDesktop = (event: MediaQueryListEvent) => {
      if (event.matches) setOpen(false);
    };
    desktop.addEventListener("change", closeOnDesktop);
    return () => desktop.removeEventListener("change", closeOnDesktop);
  }, []);

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        menu.current?.focus();
      }
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  return (
    <header className={page === "" ? "home-header" : undefined}>
      <a
        className="forged-brand"
        href="/"
        aria-label="P2V Basketball Academy home"
      >
        <img
          src="/assets/forged-logo.png"
          alt="P2V Basketball Academy"
          width="400"
          height="95"
        />
      </a>
      <Button
        ref={menu}
        type="button"
        className="menu"
        aria-expanded={open}
        aria-controls="navigation"
        onClick={() => setOpen(!open)}
      >
        Menu <span aria-hidden="true">{open ? "−" : "＋"}</span>
      </Button>
      <nav
        id="navigation"
        aria-label="Main navigation"
        className={open ? "open" : undefined}
      >
        {links.map(([slug, label]) => (
          <a
            key={slug}
            href={`/${slug}.html`}
            className={slug === "contact" ? "navcta" : undefined}
            aria-current={page === `/${slug}` ? "page" : undefined}
            onClick={() => setOpen(false)}
          >
            {label}
          </a>
        ))}
      </nav>
    </header>
  );
}
