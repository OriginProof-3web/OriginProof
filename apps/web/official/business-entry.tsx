import { useEffect, useState } from "react";
import { logout } from "./api-client.js";
import { createRoot } from "react-dom/client";
import { Building2, KeyRound, FileText, History } from "lucide-react";
import SidebarNav from "./components/primitives/SidebarNav";
import BusinessWorkspace from "./components/business/BusinessWorkspace";

const actions = window as typeof window & { selectAction: (key: string, proofId?: string) => void; showLanding: () => void };
function BusinessSidebar() {
  const [activeNav, setActiveNav] = useState("status");
  const [org, setOrg] = useState("bank");
  useEffect(() => {
    const change = (event: Event) => setActiveNav((event as CustomEvent).detail.key);
    const changeOrg = (event: Event) => setOrg((event as CustomEvent).detail);
    window.addEventListener("originproof-action", change);
    window.addEventListener("originproof-business-org", changeOrg);
    return () => { window.removeEventListener("originproof-action", change); window.removeEventListener("originproof-business-org", changeOrg); };
  }, []);
  return <SidebarNav fill activeNav={activeNav} newChatLabel="새 Proof 발행" recentTitle="발행 기록"
    navItems={[
      { key: "status", label: "기관 상태", icon: <Building2 size={18} /> },
      { key: "keys", label: "공개키 관리", icon: <KeyRound size={18} /> },
      { key: "proofs", label: "발행 목록", icon: <FileText size={18} /> },
      { key: "operations", label: "작업 이력", icon: <History size={18} /> },
    ]}
    onNewChat={() => actions.selectAction("issue")}
    onNavigate={(key) => actions.selectAction(key)}
    onPick={(id) => actions.selectAction("proofs", id)}
    onSignOut={() => { void logout(); }} footerLabel="도움말"
    onFooterClick={() => alert("자기 기관 상태, 공개키 관리, Proof 발행·목록과 작업 이력을 확인할 수 있습니다. Proof 폐기·사용 API는 제공 대기 중입니다.")}
    recents={[]}
  />;
}
createRoot(document.getElementById("sidebar-root")!).render(<BusinessSidebar />);
createRoot(document.getElementById("business-workspace-root")!).render(<BusinessWorkspace />);
