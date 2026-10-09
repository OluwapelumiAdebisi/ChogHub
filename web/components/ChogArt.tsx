import type { Traits } from "@/lib/types";

// Burst behind the Chog, by background trait.
const BURST: Record<string, [string, string]> = {
  Purple: ["#FF7AC6", "#FF93D2"],
  Night: ["#6C3BFF", "#7D52FF"],
  Mint: ["#3DDC97", "#5CE5A9"],
  Sunset: ["#FF9F43", "#FFB266"],
};

/** The NFT's own image when it has one; otherwise a drawn Chog that follows its traits. */
export function ChogArt({ image, traits, tokenId }: { image: string | null; traits: Traits; tokenId: number }) {
  const [a, b] = BURST[traits.background] ?? BURST.Purple;
  return (
    <div className="relative aspect-square w-full overflow-hidden" style={{ backgroundColor: a }}>
      <div
        aria-hidden
        className="absolute inset-0"
        style={{ backgroundImage: `repeating-conic-gradient(${b} 0 12deg, ${a} 12deg 24deg)` }}
      />
      {image ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={image} alt={`Chog #${tokenId}`} className="relative h-full w-full object-cover" />
      ) : (
        <Drawn traits={traits} tokenId={tokenId} />
      )}
    </div>
  );
}

function Drawn({ traits, tokenId }: { traits: Traits; tokenId: number }) {
  const sleepy = traits.mood === "Sleepy";
  const hyped = traits.mood === "Hyped";
  return (
    <svg viewBox="0 0 200 200" role="img" aria-label={`Chog #${tokenId}`} className="relative mx-auto h-full w-[88%]">
      <path d="M100 52c44 0 72 30 72 70 0 38-30 56-72 56s-72-18-72-56c0-40 28-70 72-70z" fill="#8F6BFF" stroke="#1B0B3A" strokeWidth="6" />
      <circle cx="70" cy="64" r="24" fill="#8F6BFF" stroke="#1B0B3A" strokeWidth="6" />
      <circle cx="130" cy="64" r="24" fill="#8F6BFF" stroke="#1B0B3A" strokeWidth="6" />
      <path d="M50 80q50 30 100 0" fill="#8F6BFF" />
      {sleepy ? (
        <path d="M58 66h24M118 66h24" stroke="#1B0B3A" strokeWidth="6" strokeLinecap="round" />
      ) : (
        <>
          <circle cx="70" cy="64" r="15" fill="#fff" stroke="#1B0B3A" strokeWidth="4" />
          <circle cx="130" cy="64" r="15" fill="#fff" stroke="#1B0B3A" strokeWidth="4" />
          <circle cx="75" cy="67" r={hyped ? 9 : 7} fill="#1B0B3A" />
          <circle cx="125" cy="61" r={hyped ? 9 : 7} fill="#1B0B3A" />
        </>
      )}
      <path d="M74 124q26 24 52 0" stroke="#1B0B3A" strokeWidth="6" fill="#FF4F9A" strokeLinecap="round" />
      {traits.hat === "Pirate Hat" && (
        <g>
          <path d="M44 42q56-60 112 0q-56-16-112 0z" fill="#1B0B3A" />
          <circle cx="100" cy="26" r="7" fill="#fff" />
        </g>
      )}
      {traits.hat === "Crown" && <path d="M72 40l8-24 20 16 20-16 8 24z" fill="#FFE14D" stroke="#1B0B3A" strokeWidth="5" strokeLinejoin="round" />}
      {traits.hat === "Beanie" && <path d="M58 44q42-50 84 0z" fill="#3DDC97" stroke="#1B0B3A" strokeWidth="5" />}
      {traits.hat === "Party Hat" && <path d="M86 40l14-38 14 38z" fill="#FFE14D" stroke="#1B0B3A" strokeWidth="5" strokeLinejoin="round" />}
    </svg>
  );
}
