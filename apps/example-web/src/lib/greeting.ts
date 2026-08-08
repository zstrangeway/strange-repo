/**
 * Build the greeting shown on the home page.
 *
 * Trims surrounding whitespace and falls back to "world" when no usable name
 * is supplied.
 */
export function greet(name?: string | null): string {
  const trimmed = name?.trim() ?? "";
  return `Hello, ${trimmed === "" ? "world" : trimmed}!`;
}
