import { logout } from "../lib/auth";

interface SignOutButtonProps {
  onSignedOut: () => void;
}

export function SignOutButton({ onSignedOut }: SignOutButtonProps) {
  return (
    <button
      type="button"
      className="dom-btn dom-btn--ghost dom-signout"
      onClick={() => {
        void logout()
          .then(() => onSignedOut())
          .catch(() => onSignedOut());
      }}
    >
      Sign out
    </button>
  );
}
