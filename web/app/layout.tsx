import type { Metadata } from "next";
// Self-hosted fonts: no Google request, no layout shift waiting on a third party.
import "@fontsource/lilita-one/400.css";
import "@fontsource/outfit/400.css";
import "@fontsource/outfit/500.css";
import "@fontsource/outfit/600.css";
import "@fontsource/outfit/700.css";
import "@fontsource/outfit/800.css";
import "./globals.css";
import { Header } from "@/components/Header";
import { Providers } from "@/components/Providers";

export const metadata: Metadata = {
  title: "ChogHub",
  description: "Your Chog is your identity and your agent in the Chog ecosystem on Monad.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <Header />
          <main className="mx-auto max-w-[1360px] px-4 pb-24 sm:px-10">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
