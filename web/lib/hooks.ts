"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { ChogProfile } from "./types";

/** Loads a Chog's public profile and remembers which sticker is newest, for the slap animation. */
export function useChogProfile(tokenId: number | null) {
  const [profile, setProfile] = useState<ChogProfile | null>(null);
  const [newest, setNewest] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const seen = useRef<Set<string> | null>(null);

  const load = useCallback(async () => {
    if (tokenId == null) return;
    try {
      const p = await api<ChogProfile>(`/chogs/${tokenId}`);
      if (seen.current) {
        const fresh = p.achievements.find((a) => !seen.current!.has(a.slug));
        if (fresh) setNewest(fresh.slug);
      }
      seen.current = new Set(p.achievements.map((a) => a.slug));
      setProfile(p);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't load this Chog");
    }
  }, [tokenId]);

  useEffect(() => {
    seen.current = null;
    setNewest(null);
    load();
  }, [load]);

  return { profile, newest, error, reload: load };
}
