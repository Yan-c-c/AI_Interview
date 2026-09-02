import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "智能面试助手",
  description: "简历评估 Agent 与多专家圆桌会议诊断",
  icons: {
    icon: "/ai-interview-metal-logo.svg",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
