import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sapira BOM Pipeline — Aceros Ibéricos Pilot",
  description:
    "Multi-agent BOM ingestion: extract from email, validate, reconcile to SAP, draft PO.",
  icons: {
    icon: [
      { url: "/favicon.ico", type: "image/x-icon" },
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/icon.svg", type: "image/svg+xml" },
    ],
    shortcut: "/favicon.ico",
    apple: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" style={{ colorScheme: "light" }}>
      <body className="antialiased bg-bg-secondary text-celo-text-primary">
        {children}
      </body>
    </html>
  );
}
