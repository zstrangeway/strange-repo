"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { me } from "./gary";
import type { User } from "./api";

type Session = {
  user: User | null;
  /** False only once gary-api has answered. Every guard has to wait for it,
   *  or a signed-in person is bounced to the login page on every reload. */
  loading: boolean;
  reload: () => Promise<void>;
};

const SessionContext = createContext<Session>({
  user: null,
  loading: true,
  reload: async () => {},
});

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setUser(await me());
    setLoading(false);
  }, []);

  useEffect(() => {
    // Asking gary-api who this is, on mount. Not derived state — the answer
    // lives outside React and there is no way to have it before asking.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void reload();
  }, [reload]);

  return (
    <SessionContext.Provider value={{ user, loading, reload }}>
      {children}
    </SessionContext.Provider>
  );
}

/** Who is signed in, shared by everything under the app layout so the sidebar
 *  and the page do not each ask gary-api the same question. */
export function useSession(): Session {
  return useContext(SessionContext);
}
