import { useEffect, useState } from "react";
import type { AuthUser } from "../lib/auth";
import { fetchAuthUser } from "../lib/auth";
import { resolveAppView } from "../lib/routing";
import { clearLegacyApiKeyStorage } from "../lib/session";
import { ChatApp } from "./ChatApp";
import { ConnectionsView } from "./ConnectionsView";
import { NotAllowedScreen } from "./NotAllowedScreen";
import { SignInScreen } from "./SignInScreen";

type AuthState = "loading" | "signed-out" | "signed-in";

export function AppShell() {
  const [authState, setAuthState] = useState<AuthState>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);
  const view = resolveAppView();

  useEffect(() => {
    clearLegacyApiKeyStorage();
  }, []);

  useEffect(() => {
    if (view === "not-allowed") {
      setAuthState("signed-out");
      return;
    }

    let cancelled = false;
    void fetchAuthUser()
      .then((authUser) => {
        if (cancelled) {
          return;
        }
        if (!authUser) {
          setUser(null);
          setAuthState("signed-out");
          return;
        }
        setUser(authUser);
        setAuthState("signed-in");
      })
      .catch(() => {
        if (!cancelled) {
          setUser(null);
          setAuthState("signed-out");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [view]);

  const handleSignedOut = () => {
    setUser(null);
    setAuthState("signed-out");
    window.location.assign(`${import.meta.env.BASE_URL}`);
  };

  if (view === "not-allowed") {
    return (
      <main className="dom-app dom-app--auth">
        <NotAllowedScreen />
      </main>
    );
  }

  if (authState === "loading") {
    return (
      <main className="dom-app dom-app--auth">
        <div className="dom-auth">
          <div className="dom-auth__main">
            <p className="dom-auth__lede">Loading…</p>
          </div>
        </div>
      </main>
    );
  }

  if (authState === "signed-out") {
    return (
      <main className="dom-app dom-app--auth">
        <SignInScreen />
      </main>
    );
  }

  return (
    <main className="dom-app">
      {view === "connections" ? (
        <ConnectionsView user={user} onSignOut={handleSignedOut} />
      ) : (
        <ChatApp user={user} onSignOut={handleSignedOut} />
      )}
    </main>
  );
}
