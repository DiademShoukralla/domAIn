import { useState } from "react";
import { githubLoginUrl, landingPageUrl } from "../lib/auth";
import { DomMark } from "./DomMark";

export function SignInScreen() {
  const [redirecting, setRedirecting] = useState(false);

  const handleSignIn = () => {
    setRedirecting(true);
    window.location.assign(githubLoginUrl());
  };

  return (
    <div className="dom-auth">
      <div className="dom-auth__main">
        <DomMark />
        <div className="dom-auth__copy">
          <h1 className="dom-auth__title">Sign in to domAIn</h1>
          <p className="dom-auth__lede">
            domAIn is private for now. Use the GitHub account I&apos;ve invited.
          </p>
        </div>
        <button
          type="button"
          className="dom-auth__github-btn"
          onClick={handleSignIn}
          disabled={redirecting}
        >
          <img src={`${import.meta.env.BASE_URL}github-mark.svg`} alt="" className="dom-auth__github-mark" />
          {redirecting ? "Taking you to GitHub…" : "Sign in with GitHub"}
        </button>
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
