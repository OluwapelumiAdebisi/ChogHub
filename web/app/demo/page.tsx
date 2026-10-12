import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "ChogHub demo",
  description: "We didn't give an NFT utility. We gave the NFT a job. A 3-minute tour of ChogHub on Monad: the story, then the live app.",
};

export default function Demo() {
  return (
    <div className="py-8">
      <h1 className="text-[clamp(40px,6vw,64px)]">The ChogHub demo</h1>
      <p className="mt-2 max-w-[60ch] text-[19px] font-semibold">
        We didn&apos;t give an NFT utility. We gave the NFT a job.
      </p>
      <div className="mt-6 overflow-hidden rounded-[28px] border-4 border-ink bg-ink shadow-hard-lg">
        <video
          className="block aspect-video w-full"
          src="/choghub-demo.mp4"
          poster="/choghub-demo-poster.jpg"
          controls
          playsInline
          preload="metadata"
        />
      </div>
      <div className="mt-8 flex flex-wrap gap-3">
        <Link href="/hub" className="btn-primary">
          Try it with your Chog
        </Link>
        <a href="https://github.com/OluwapelumiAdebisi/ChogHub" target="_blank" rel="noreferrer" className="btn-quiet">
          See the code
        </a>
      </div>
    </div>
  );
}
