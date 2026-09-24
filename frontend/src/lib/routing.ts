export type AppView = "chat" | "connections";

export function resolveAppView(pathname: string = window.location.pathname): AppView {
  const normalized = pathname.replace(/\/+$/, "");
  return normalized.endsWith("/connections") ? "connections" : "chat";
}

export interface ConnectionCallbackParams {
  provider: string | null;
  status: string | null;
}

export function parseConnectionCallback(
  search: string = window.location.search,
): ConnectionCallbackParams {
  const params = new URLSearchParams(search);
  return {
    provider: params.get("provider"),
    status: params.get("status"),
  };
}

export function appPath(view: AppView = "chat"): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, "");
  return view === "connections" ? `${base}/connections` : `${base}/`;
}

export function providerDisplayName(provider: string): string {
  if (provider === "github") {
    return "GitHub";
  }
  if (provider === "linear") {
    return "Linear";
  }
  return provider;
}
