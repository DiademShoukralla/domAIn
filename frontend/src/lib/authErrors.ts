export function humanizeApiError(status: number, rawDetail: string): string {
  let detail = rawDetail.trim();
  try {
    const parsed = JSON.parse(rawDetail) as { detail?: unknown };
    if (typeof parsed.detail === "string") {
      detail = parsed.detail;
    }
  } catch {
    // keep raw text
  }

  if (status === 401) {
    if (detail === "Not authenticated" || detail === "Invalid API key") {
      return "Your session has ended. Sign in again to keep going.";
    }
    return "Your session has ended. Sign in again to keep going.";
  }

  if (status === 403) {
    return "You do not have access to that action.";
  }

  if (status >= 500) {
    return "Something went wrong on our side. Try again in a moment.";
  }

  if (detail) {
    return detail;
  }

  return `Request failed with status ${status}`;
}
