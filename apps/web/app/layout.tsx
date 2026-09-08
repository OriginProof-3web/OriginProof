import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "OriginProof MVP 데모",
  description: "합성 카드 결제 알림의 검증 흐름을 확인하는 내부 MVP 데모",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
