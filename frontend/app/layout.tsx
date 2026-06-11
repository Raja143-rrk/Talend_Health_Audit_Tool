import type { ReactNode } from "react";
import type { Metadata } from "next";

import { ThemeProvider } from "@/components/providers/theme-provider";

import "./globals.css";

const appName = process.env.NEXT_PUBLIC_APP_NAME ?? "Talend Health Analyzer";

export const metadata: Metadata = {
  title: appName,
  description: "Operational dashboard for Talend job health and audit visibility.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
