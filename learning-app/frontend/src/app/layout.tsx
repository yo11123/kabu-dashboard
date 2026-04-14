import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Python学習ダッシュボード",
  description: "Python・機械学習・深層学習・生成AIをインタラクティブに学ぶ",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja" className="h-full">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+JP:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&family=Cormorant+Garamond:wght@500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="h-full bg-bg-base text-ivory antialiased">
        {children}
      </body>
    </html>
  );
}
