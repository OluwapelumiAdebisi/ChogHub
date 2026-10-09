// Stroke icons, ink by default. Decorative: the label beside them carries the meaning.
type P = { className?: string };
const base = { width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2.5, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true };

export const Star = (p: P) => (
  <svg {...base} {...p}><path d="M12 3l2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.5 6.7 19.4l1.2-6L3.4 9.3l6-.7z" /></svg>
);
export const Mic = (p: P) => (
  <svg {...base} {...p}><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></svg>
);
export const Coin = (p: P) => (
  <svg {...base} {...p}><circle cx="12" cy="12" r="8" /><path d="M12 8v8M9 11h6" /></svg>
);
export const Anchor = (p: P) => (
  <svg {...base} {...p}><circle cx="12" cy="5" r="2" /><path d="M12 7v14M5 13a7 7 0 0 0 14 0M8 10h8" /></svg>
);
export const Trophy = (p: P) => (
  <svg {...base} {...p}><path d="M8 4h8v5a4 4 0 0 1-8 0zM8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4M12 13v4M8 21h8" /></svg>
);

export const BADGE_ICON: Record<string, (p: P) => JSX.Element> = { frog: Star, mic: Mic, coin: Coin, anchor: Anchor, trophy: Trophy };
