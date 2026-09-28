import { useEffect, useState } from "react";
import {
  fetchAccessDeniedInfo,
  githubLoginUrl,
  githubLogoutUrl,
  initialsFromLogin,
  landingPageUrl,
  requestAccessMailto,
} from "../lib/auth";
import { appPath } from "../lib/routing";

export function NotAllowedScreen() {
  const [login, setLogin] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchAccessDeniedInfo()
      .then((info) => {
        if (!info) {
          window.location.replace(appPath("chat"));
          return;
        }
        setLogin(info.login);
      })
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : "Could not load your account.");
      });
  }, []);

  if (error) {
    return (
      <div className="dom-auth">
        <div className="dom-auth__main">
          <p className="dom-auth__lede">{error}</p>
          <a className="dom-auth__secondary-btn" href={githubLoginUrl()}>
            Try signing in again
          </a>
        </div>
      </div>
    );
  }

  if (!login) {
    return (
      <div className="dom-auth">
        <div className="dom-auth__main">
          <p className="dom-auth__lede">Loading your account…</p>
        </div>
      </div>
    );
  }

  const initials = initialsFromLogin(login);

  return (
    <div className="dom-auth">
      <div className="dom-auth__main">
        <div className="dom-auth__identity">
          <span className="dom-auth__avatar" aria-hidden="true">
            {initials}
          </span>
          <span className="dom-auth__identity-text">
            Signed in as <strong>@{login}</strong>
          </span>
        </div>
        <div className="dom-auth__copy">
          <h1 className="dom-auth__title">You&apos;re not on the list yet</h1>
          <p className="dom-auth__lede">
            domAIn is invite-only while I build it. If you&apos;d like to try it, send me your GitHub
            username and I&apos;ll add you.
          </p>
        </div>
        <div className="dom-auth__actions">
          <a className="dom-auth__primary-btn" href={requestAccessMailto(login)}>
            Request access
          </a>
          <a
            className="dom-auth__secondary-btn"
            href={githubLogoutUrl()}
            target="_blank"
            rel="noopener noreferrer"
          >
            Use a different account
          </a>
          <p className="dom-auth__hint caption">
            Sign out of GitHub first in the new tab, then try again.
          </p>
        </div>
      </div>
      <p className="dom-auth__footer">
        Back to{" "}
        <a className="dom-auth__link" href={landingPageUrl()}>
          domain.didi.build
        </a>
      </p>
    </div>
  );
}
