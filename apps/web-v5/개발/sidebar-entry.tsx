import { useEffect, useState } from "react";
import { logout } from "./api-client.js";
import { createRoot } from "react-dom/client";
import SidebarNav from "./components/primitives/SidebarNav";
import UserWorkspace from "./components/user/UserWorkspace";

const actions = window as typeof window & {
  selectAction: (key: string, proofId?: string) => void;
  showLanding: () => void;
};

function WorkspaceSidebar() {
  const [activeNav, setActiveNav] = useState("home");
  useEffect(() => {
    const change = (event: Event) => { const key = (event as CustomEvent).detail.key; setActiveNav(key === "history" ? "history" : key === "home" ? "home" : "chats"); };
    window.addEventListener("originproof-action", change);
    return () => window.removeEventListener("originproof-action", change);
  }, []);
  return <SidebarNav
    fill
    activeNav={activeNav}
    onNewChat={() => actions.selectAction("verify")}
    onNavigate={(key) => { setActiveNav(key); actions.selectAction(key); }}
    onPick={(id) => actions.selectAction("verify", id)}
    onSignOut={() => { void logout(); }}
    footerLabel="도움말"
    onFooterClick={() => alert("Proof ID 조회와 자료 내용 비교를 이용할 수 있습니다. 지정 수신자는 1회 사용을 요청하고 미확인 거래 상태를 조회할 수 있습니다.")}
    recents={[]}
  />;
}

createRoot(document.getElementById("sidebar-root")!).render(<WorkspaceSidebar />);

createRoot(document.getElementById("user-workspace-root")!).render(<UserWorkspace lifecycleEnabled apiPrefix="/api" />);
