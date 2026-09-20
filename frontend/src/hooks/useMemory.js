import { useEffect, useState } from "react";
import { memInit, memSnapshot, memStats, subscribe } from "../lib/memory.js";

export function useMemory() {
  const [items, setItems] = useState(() => memSnapshot());
  const [stats, setStats] = useState(() => memStats());

  useEffect(() => {
    let alive = true;
    memInit().then(() => {
      if (!alive) return;
      setItems(memSnapshot());
      setStats(memStats());
    });
    const unsub = subscribe(() => {
      setItems(memSnapshot());
      setStats(memStats());
    });
    return () => {
      alive = false;
      unsub();
    };
  }, []);

  return { items, stats };
}