import type { Metadata } from "next";
import type { ReactNode } from "react";

import "../styles/globals.css";

export const metadata: Metadata = {
  title: "LLmrab",
  description: "Deterministic frontend runtime layout.",
};

type RootLayoutProps = Readonly<{
  children: ReactNode;
}>;

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="de">
      <body>{children}</body>
    </html>
  );
}
