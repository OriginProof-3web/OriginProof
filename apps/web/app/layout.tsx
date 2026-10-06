import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "OriginProof",
  description: "발행 기록 조회와 자료 내용 비교",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
