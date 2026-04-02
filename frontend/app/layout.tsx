import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mahi — Mental Health Companion",
  description: "Ek safe space — apni baat karo, bina judge ke.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="h-full">{children}</body>
    </html>
  );
}
