type ApiFailure = { error?: string; detail?: string };

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
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

