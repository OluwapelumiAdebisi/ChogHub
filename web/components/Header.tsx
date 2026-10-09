"use client";

import { ConnectButton } from "@rainbow-me/rainbowkit";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession } from "@/lib/session";

export function Header() {
  const path = usePathname();
  const { token, isAdmin } = useSession();
  const links = [
    { href: "/hub", label: "My Chog" },
    { href: "/events", label: "Events" },
    { href: "/quests", label: "Quests" },
    ...(isAdmin ? [{ href: "/admin", label: "Admin" }] : []),
  ];
  return (
    <header className="mx-auto flex max-w-[1360px] flex-wrap items-center gap-x-6 gap-y-4 px-4 py-5 sm:px-10">
      <Link
        href={token ? "/hub" : "/"}
        className="title-pop -rotate-3 font-display text-[38px] leading-none text-grape"
        aria-label="ChogHub home"
      >
        ChogHub
      </Link>
      <nav aria-label="Main" className="order-3 flex w-full flex-wrap gap-2.5 sm:order-none sm:w-auto">
        {links.map((l) => {
          const active = path.startsWith(l.href);
          return (
            <Link
              key={l.href}
              href={l.href}
              aria-current={active ? "page" : undefined}
              className={`rounded-full border-3 border-ink px-[18px] py-2 font-extrabold ${
                active ? "bg-ink text-sun" : "bg-white text-ink hover:bg-bubble-light"
              }`}
            >
              {l.label}
            </Link>
          );
        })}
      </nav>
      <div className="ml-auto">
        <ConnectButton chainStatus="icon" showBalance={false} accountStatus="address" label="Connect wallet" />
      </div>
    </header>
  );
}
