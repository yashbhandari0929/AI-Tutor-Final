// LOCATION: app/layout.tsx
import type { Metadata } from "next";
import { Geist, Geist_Mono, Noto_Sans_Devanagari } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// Renders Devanagari (Hindi/Marathi/Sanskrit) text — Geist has no glyphs
// for this script at all, so without this, Devanagari falls back to
// whatever the OS happens to provide (often nothing, i.e. tofu boxes).
const notoDevanagari = Noto_Sans_Devanagari({
  variable: "--font-noto-devanagari",
  subsets: ["devanagari"],
  weight: ["400", "600"],
});

export const metadata: Metadata = {
  title: "AI Tutor",
  description: "Personal AI Tutor",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${notoDevanagari.variable} h-full antialiased`}
    >
      <body className="h-full">
        {children}
      </body>
    </html>
  );
}