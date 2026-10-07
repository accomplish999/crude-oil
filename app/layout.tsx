import type { Metadata, Viewport } from "next";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { siteUrl } from "@/lib/archive";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Crude oil",
    template: "%s | Crude oil",
  },
  description:
    "EIA spots, weekly stocks, the four NYMEX contracts EIA publishes, and CFTC managed money. Every point keeps its source and retrieval date.",
  applicationName: "Crude oil",
  robots: { index: true, follow: true },
  icons: { icon: "/favicon.svg" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#000000",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip" href="#content">
          Skip to content
        </a>
        <Header />
        <div className="band" aria-hidden="true" />
        <main id="content" className="shell">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
