"use client"

// Not a shadcn registry component — the registry has no theme control; its
// docs point you at next-themes. This is the part of next-themes worth having,
// without the dependency.
//
// A provider rather than a bare hook, and mounted at the root rather than
// beside the control: the stored choice has to be applied on every page load,
// and a hook living inside a dropdown only runs once someone opens the
// dropdown. That bug is what the "survives a reload" scenario caught.

import * as React from "react"

export type Theme = "light" | "dark" | "system"

const STORAGE_KEY = "theme"
const CHOICES: readonly Theme[] = ["light", "dark", "system"]

function isTheme(value: unknown): value is Theme {
  return typeof value === "string" && CHOICES.includes(value as Theme)
}

function read(): Theme {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    return isTheme(stored) ? stored : "system"
  } catch {
    // Safari with site data blocked throws here rather than returning null.
    // Following the system is the right answer in that case anyway.
    return "system"
  }
}

/**
 * "system" removes both classes rather than adding one: the stylesheet's
 * prefers-color-scheme block is what follows the machine, and a class here
 * would sit in front of it and win.
 */
function apply(theme: Theme) {
  const root = document.documentElement
  root.classList.remove("light", "dark")
  if (theme !== "system") {
    root.classList.add(theme)
  }
  // Without this a dark page still gets light scrollbars and form controls.
  root.style.colorScheme = theme === "system" ? "light dark" : theme
}

const ThemeContext = React.createContext<{
  theme: Theme
  setTheme: (theme: Theme) => void
} | null>(null)

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<Theme>("system")

  // After mount, not during render: the server rendered without knowing the
  // stored choice, so reading it during render would disagree with the HTML
  // the server sent and trip hydration. The cost is a frame of the system
  // theme before an overriding choice takes effect.
  React.useEffect(() => {
    const stored = read()
    setThemeState(stored)
    apply(stored)
  }, [])

  const setTheme = React.useCallback((next: Theme) => {
    setThemeState(next)
    apply(next)
    try {
      window.localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Nothing to do — the choice simply will not outlive the tab.
    }
  }, [])

  const value = React.useMemo(() => ({ theme, setTheme }), [theme, setTheme])

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = React.useContext(ThemeContext)
  if (!context) {
    throw new Error("useTheme has to be used inside a <ThemeProvider>")
  }
  return context
}
