"use client";

import { FormEvent, useEffect, useState } from "react";

type Role = "operator" | "issuer" | "recipient";

type Account = {
  account_id: string;
  username: string;
  role: Role;
  issuer_id: string | null;
  csrf_token: string;
};

type Application = {
  application_id: string;
  issuer_id: string;
  issuer_name: string;
  applicant_account_id: string;
  status: string;
  decision_reason: string | null;
  decided_by_account_id: string | null;
  created_at: string;
};

type ApiFailure = { error?: string; detail?: string };

const roleLabels: Record<Role, string> = {
  operator: "운영자",
  issuer: "발행기관 담당자",
  recipient: "수신자",
};

const statusLabels: Record<string, string> = {
  PENDING_REVIEW: "검토 대기",
  APPROVED_PENDING_CHAIN: "승인됨 · 체인 활성화 대기",
  REJECTED: "반려됨",
};

function apiMessage(code: string): string {
  const messages: Record<string, string> = {
    AUTH_REQUIRED: "세션이 만료되었습니다. 다시 로그인해 주세요.",
    INVALID_CREDENTIALS: "계정 이름 또는 비밀번호를 확인해 주세요.",
    CSRF_REQUIRED: "요청을 확인할 수 없습니다. 화면을 새로고침한 뒤 다시 시도해 주세요.",
    FORBIDDEN: "이 작업을 수행할 권한이 없습니다.",
    INVALID_ISSUER: "기관 이름을 확인해 주세요.",
    APPLICATION_EXISTS: "이미 신청이 있습니다. 신청 상태를 다시 조회해 주세요.",
    REASON_REQUIRED: "검토 사유를 입력해 주세요.",
    ALREADY_DECIDED: "이미 검토가 끝난 신청입니다. 목록을 새로고침해 주세요.",
    SELF_APPROVAL_FORBIDDEN: "본인 기관의 신청은 승인할 수 없습니다.",
  };
  return messages[code] ?? "요청을 처리하지 못했습니다. 잠시 후 상태를 다시 확인해 주세요.";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  const payload = (await response.json().catch(() => ({}))) as T & ApiFailure;
  if (!response.ok) {
    throw new Error(payload.detail ?? payload.error ?? `HTTP_${response.status}`);
  }
  return payload;
}

function isRole(value: string): value is Role {
  return value === "operator" || value === "issuer" || value === "recipient";
}

function statusLabel(status: string): string {
  return statusLabels[status] ?? "상태 확인 필요";
}

export default function FinalsPage() {
  const [account, setAccount] = useState<Account | null>(null);
  const [application, setApplication] = useState<Application | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  async function loadRoleData(current: Account) {
    if (current.role === "issuer") {
      const ownApplication = await request<Application | null>("/v1/issuer-applications/mine");
      setApplication(ownApplication);
    } else if (current.role === "operator") {
      const rows = await request<Application[]>("/v1/operator/issuer-applications");
      setApplications(rows);
    }
  }

  async function refreshRoleData() {
    if (!account) return;
    setError(null);
    setInfo(null);
    setIsSubmitting(true);
    try {
      await loadRoleData(account);
      setInfo("현재 신청 상태를 다시 조회했습니다.");
    } catch (reason) {
      reportFailure(reason);
    } finally {
      setIsSubmitting(false);
    }
  }

  function reportFailure(reason: unknown) {
    const code = reason instanceof Error ? reason.message : "REQUEST_FAILED";
    if (code === "AUTH_REQUIRED") {
      setAccount(null);
      setApplication(null);
      setApplications([]);
    }
    setError(apiMessage(code));
  }

  useEffect(() => {
    let active = true;
    request<Account>("/v1/auth/me")
      .then(async (current) => {
        if (!isRole(current.role)) throw new Error("UNSUPPORTED_ROLE");
        await loadRoleData(current);
        if (active) setAccount(current);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        if (reason instanceof Error && reason.message !== "AUTH_REQUIRED") {
          setError(apiMessage(reason.message));
        }
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    setError(null);
    setInfo(null);
    setIsSubmitting(true);
    const form = new FormData(formElement);
    try {
      const current = await request<Account>("/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({
          username: String(form.get("username") ?? ""),
          password: String(form.get("password") ?? ""),
        }),
      });
      if (!isRole(current.role)) throw new Error("UNSUPPORTED_ROLE");
      await loadRoleData(current);
      setAccount(current);
      formElement.reset();
    } catch (reason) {
      reportFailure(reason);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function logout() {
    if (!account) return;
    setError(null);
    setInfo(null);
    setIsSubmitting(true);
    try {
      await request("/v1/auth/logout", {
        method: "POST",
        headers: { "X-CSRF-Token": account.csrf_token },
      });
      setAccount(null);
      setApplication(null);
      setApplications([]);
      setInfo("로그아웃했습니다.");
    } catch (reason) {
      const code = reason instanceof Error ? reason.message : "REQUEST_FAILED";
      if (code === "AUTH_REQUIRED") {
        setAccount(null);
        setApplication(null);
        setApplications([]);
      }
      setError(apiMessage(code));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function submitApplication(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!account) return;
    const formElement = event.currentTarget;
    setError(null);
    setInfo(null);
    setIsSubmitting(true);
    const form = new FormData(formElement);
    try {
      const created = await request<Application>("/v1/issuer-applications", {
        method: "POST",
        headers: { "X-CSRF-Token": account.csrf_token },
        body: JSON.stringify({ issuer_name: String(form.get("issuer_name") ?? "") }),
      });
      setApplication(created);
      setInfo("신청을 제출했습니다. 운영자 검토를 기다려 주세요.");
      formElement.reset();
    } catch (reason) {
      reportFailure(reason);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function decide(event: FormEvent<HTMLFormElement>, row: Application) {
    event.preventDefault();
    if (!account) return;
    setError(null);
    setInfo(null);
    setIsSubmitting(true);
    const form = new FormData(event.currentTarget);
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    const decision = submitter?.value === "REJECT" ? "REJECT" : "APPROVE";
    try {
      const updated = await request<Application>(
        `/v1/operator/issuer-applications/${encodeURIComponent(row.application_id)}/decision`,
        {
          method: "POST",
          headers: { "X-CSRF-Token": account.csrf_token },
          body: JSON.stringify({ decision, reason: String(form.get("reason") ?? "") }),
        },
      );
      setApplications((current) => current.map((item) => item.application_id === updated.application_id ? updated : item));
      setInfo(decision === "APPROVE" ? "신청 검토를 저장했습니다. 체인 활성화 상태는 별도로 확인해야 합니다." : "반려 결정을 저장했습니다.");
    } catch (reason) {
      reportFailure(reason);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="finals-page">
      <header className="finals-header">
        <div>
          <p className="eyebrow">ORIGINPROOF · FINALS W1</p>
          <h1>계정과 기관 신청</h1>
          <p className="subtitle">준비된 테스트 계정으로 로그인하고, 서버가 확인한 역할에 맞는 화면을 사용합니다.</p>
        </div>
        {account && (
          <div className="account-strip">
            <span>{account.username} · {roleLabels[account.role]}</span>
            <button type="button" onClick={logout} disabled={isSubmitting}>로그아웃</button>
          </div>
        )}
      </header>

      {error && <p className="finals-message finals-error" role="alert">{error}</p>}
      {info && <p className="finals-message finals-info" role="status">{info}</p>}

      {isLoading ? (
        <p className="finals-message" role="status">현재 세션을 확인하고 있습니다.</p>
      ) : !account ? (
        <section className="finals-card" aria-labelledby="login-heading">
          <h2 id="login-heading">테스트 계정 로그인</h2>
          <p>회원가입이나 역할 선택은 제공하지 않습니다. 권한은 로그인한 계정에서 확인합니다.</p>
          <form className="finals-form" onSubmit={login}>
            <label>계정 이름<input name="username" autoComplete="username" required /></label>
            <label>비밀번호<input name="password" type="password" autoComplete="current-password" required /></label>
            <button type="submit" disabled={isSubmitting}>{isSubmitting ? "로그인 중…" : "로그인"}</button>
          </form>
        </section>
      ) : account.role === "issuer" ? (
        <section className="finals-card" aria-labelledby="issuer-heading">
          <h2 id="issuer-heading">발행기관 신청</h2>
          <p>기관 ID는 계정에 연결되어 있습니다. 신청 화면에서 다른 기관이나 역할을 선택할 수 없습니다.</p>
          <button className="refresh-button" type="button" onClick={refreshRoleData} disabled={isSubmitting}>신청 상태 새로고침</button>
          {application ? (
            <ApplicationSummary application={application} />
          ) : (
            <form className="finals-form" onSubmit={submitApplication}>
              <label>합성 기관 이름<input name="issuer_name" maxLength={120} required /></label>
              <button type="submit" disabled={isSubmitting}>{isSubmitting ? "제출 중…" : "신청 제출"}</button>
            </form>
          )}
        </section>
      ) : account.role === "operator" ? (
        <section className="finals-card" aria-labelledby="operator-heading">
          <h2 id="operator-heading">기관 신청 검토</h2>
          <button className="refresh-button" type="button" onClick={refreshRoleData} disabled={isSubmitting}>신청 목록 새로고침</button>
          {applications.length === 0 ? <p>검토할 신청이 없습니다.</p> : (
            <ul className="application-list">
              {applications.map((row) => (
                <li key={row.application_id} className="application-item">
                  <ApplicationSummary application={row} />
                  {row.status === "PENDING_REVIEW" && (
                    <form className="decision-form" onSubmit={(event) => decide(event, row)}>
                      <label>검토 사유<input name="reason" maxLength={500} required /></label>
                      <button type="submit" name="decision" value="APPROVE" disabled={isSubmitting}>승인 검토</button>
                      <button type="submit" name="decision" value="REJECT" disabled={isSubmitting}>반려</button>
                    </form>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : (
        <section className="finals-card" aria-labelledby="recipient-heading">
          <h2 id="recipient-heading">수신자 계정</h2>
          <p>로그인된 수신자 계정을 확인했습니다. 공개 Proof ID 조회는 로그인과 별도 흐름이며, 제한 내용 비교는 지정된 Proof에 대해서만 요청할 수 있습니다.</p>
        </section>
      )}
    </main>
  );
}

function ApplicationSummary({ application }: { application: Application }) {
  return (
    <dl className="application-summary">
      <div><dt>기관</dt><dd>{application.issuer_name}</dd></div>
      <div><dt>신청 상태</dt><dd>{statusLabel(application.status)}</dd></div>
      {application.decision_reason && <div><dt>검토 사유</dt><dd>{application.decision_reason}</dd></div>}
      {application.status === "APPROVED_PENDING_CHAIN" && <p className="chain-pending">운영자 검토는 승인됐지만 체인 활성화는 별도 확인이 필요합니다.</p>}
    </dl>
  );
}
