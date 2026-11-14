import { useEffect, useState } from "react";
import { getHealth } from "../api/client";

export interface ServiceHealth {
  state: "checking" | "online" | "offline";
  indexReady: boolean | null;
}

export function useServiceHealth(): ServiceHealth {
  const [health, setHealth] = useState<ServiceHealth>({ state: "checking", indexReady: null });
  useEffect(() => {
    let controller: AbortController | undefined;
    let active = true;
    async function check() {
      if (document.visibilityState === "hidden") return;
      controller?.abort();
      const request = new AbortController();
      controller = request;
      try {
        const response = await getHealth(request.signal);
        if (active && !request.signal.aborted) setHealth({ state: "online", indexReady: response.index_ready });
      } catch {
        if (active && !request.signal.aborted) setHealth({ state: "offline", indexReady: null });
      }
    }
    function onVisibility() {
      if (document.visibilityState === "hidden") controller?.abort();
      else void check();
    }
    void check();
    const timer = window.setInterval(() => void check(), 30000);
    const onFocus = () => { void check(); };
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      active = false;
      controller?.abort();
      window.clearInterval(timer);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);
  return health;
}
