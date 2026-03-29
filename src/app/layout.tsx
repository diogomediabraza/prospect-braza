import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "Prospect Braza — Motor de Prospecção B2B",
  description: "Encontre, analise e priorize leads B2B com inteligência artificial. Powered by We Braza Group.",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-PT">
      <body>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 min-w-0 overflow-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
