"use client";

import { useEffect } from "react";

import { FLASH_COOKIE } from "@/lib/flash";

/** Drop the flash cookie once its message is on the screen.
 *
 * It has to happen here rather than on the server: clearing a cookie is
 * setting one, and Next only allows that in a Route Handler or a Server
 * Action — the same restriction that makes the callbacks route handlers in
 * the first place. Without this the message would show once more on the next
 * render inside its short lifetime.
 */
export function ClearFlash() {
  useEffect(() => {
    document.cookie = `${FLASH_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
  }, []);

  return null;
}
