import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ARC — Agentic Research & Work Copilot",
  description:
    "AI-powered agentic research platform that plans multi-step workflows, runs coordinated AI agents, and delivers validated reports with citations.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className="min-h-screen custom-scrollbar">{children}</body>
    </html>
  );
}
