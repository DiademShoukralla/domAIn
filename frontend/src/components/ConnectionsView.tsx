import { useCallback, useEffect, useState } from "react";
import { deleteSource, fetchSources, refreshSource } from "../lib/api";
import { appPath, parseConnectionCallback, providerDisplayName } from "../lib/routing";
import type { KnowledgeSource } from "../types/sources";
import { SourceListItem } from "./SourceListItem";

interface ConnectionsViewProps {
  apiKey: string;
}

const POLL_INTERVAL_MS = 3000;

function hasActiveSources(sources: KnowledgeSource[]): boolean {
  return sources.some((source) => source.status === "pending" || source.status === "indexing");
}

export function ConnectionsView({ apiKey }: ConnectionsViewProps) {
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [busySourceId, setBusySourceId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<string | null>(null);

  const loadSources = useCallback(async () => {
    const payload = await fetchSources(apiKey);
    setSources(payload.sources);
  }, [apiKey]);

  useEffect(() => {
    const callback = parseConnectionCallback();
    if (callback.provider && callback.status === "connected") {
      setConfirmation(`${providerDisplayName(callback.provider)} connected successfully.`);
      window.history.replaceState({}, "", appPath("connections"));
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    const refresh = async () => {
      try {
        await loadSources();
        if (!cancelled) {
          setError(null);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load sources.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void refresh();
    return () => {
      cancelled = true;
    };
  }, [loadSources]);

  useEffect(() => {
    if (!hasActiveSources(sources)) {
      return;
    }

    const timer = window.setInterval(() => {
      void loadSources().catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : "Failed to refresh sources.");
      });
    }, POLL_INTERVAL_MS);

    return () => {
      window.clearInterval(timer);
    };
  }, [loadSources, sources]);

  const handleRefresh = async (sourceId: string) => {
    setBusySourceId(sourceId);
    setError(null);
    try {
      const updated = await refreshSource(apiKey, sourceId);
      setSources((current) =>
        current.map((source) => (source.id === sourceId ? updated : source)),
      );
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Failed to refresh source.");
    } finally {
      setBusySourceId(null);
    }
  };

  const handleDelete = async (sourceId: string) => {
    setBusySourceId(sourceId);
    setError(null);
    try {
      await deleteSource(apiKey, sourceId);
      setSources((current) => current.filter((source) => source.id !== sourceId));
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Failed to delete source.");
    } finally {
      setBusySourceId(null);
    }
  };

  return (
    <>
      <header className="dom-header layout-thread">
        <div>
          <p className="overline">domAIn</p>
          <h1 className="dom-header__title">Connections</h1>
        </div>
        <nav className="dom-nav" aria-label="App sections">
          <a className="dom-nav__link" href={appPath("chat")}>
            Chat
          </a>
          <a className="dom-nav__link dom-nav__link--active" href={appPath("connections")} aria-current="page">
            Connections
          </a>
        </nav>
      </header>

      <section className="dom-connections layout-thread">
        {confirmation ? (
          <p className="dom-connections__banner body" role="status">
            {confirmation}
          </p>
        ) : null}

        <div className="dom-connections__providers">
          <h2 className="label-strong">Connect a provider</h2>
          <p className="caption">
            GitHub uses an app install redirect. Linear uses OAuth. Both return here when complete.
          </p>
          <div className="dom-connections__provider-actions">
            <a className="dom-btn dom-btn--secondary" href="/oauth/github/authorize">
              Connect GitHub
            </a>
            <a className="dom-btn dom-btn--secondary" href="/oauth/linear/authorize">
              Connect Linear
            </a>
          </div>
        </div>

        <div className="dom-connections__sources">
          <h2 className="label-strong">Knowledge sources</h2>
          {loading ? <p className="caption">Loading sources</p> : null}
          {!loading && sources.length === 0 ? (
            <p className="caption">No knowledge sources yet. Connect a provider, then attach a source.</p>
          ) : null}
          {!loading && sources.length > 0 ? (
            <div className="dom-source-list">
              {sources.map((source) => (
                <SourceListItem
                  key={source.id}
                  source={source}
                  busy={busySourceId === source.id}
                  onRefresh={(sourceId) => {
                    void handleRefresh(sourceId);
                  }}
                  onDelete={(sourceId) => {
                    void handleDelete(sourceId);
                  }}
                />
              ))}
            </div>
          ) : null}
        </div>
      </section>

      {error ? <p className="dom-error layout-thread caption">{error}</p> : null}
    </>
  );
}
