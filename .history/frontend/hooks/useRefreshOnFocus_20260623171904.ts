// hooks/useRefreshOnFocus.ts
//
// Calls `callback` immediately on mount, then again every time the user
// returns to this browser tab or navigates back to the page.
// Drop this into hooks/ and use it in any page that shows live stats.

import { useEffect } from "react";

export function useRefreshOnFocus(callback: () => void) {
  useEffect(() => {
    // Initial load
    callback();

    // Re-fetch when the tab becomes visible again (user switches back)
    const onVisibility = () => {
      if (document.visibilityState === "visible") callback();
    };

    // Re-fetch when the window regains focus (alt-tab, click back from another window)
    const onFocus = () => callback();

    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("focus", onFocus);

    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("focus", onFocus);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // callback is stable — defined outside effect
}