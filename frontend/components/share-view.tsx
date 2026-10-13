"use client";

import { useEffect, useState } from "react";
import { apiFetch, shortWallet } from "@/lib/api";
import type { ShareView as ShareData } from "@/lib/types";

export function ShareView({ token }: { token: string }) {
  const [data, setData] = useState<ShareData | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    apiFetch<ShareData>(`/shares/${encodeURIComponent(token)}`).then(setData).catch((e: Error) => setError(e.message));
  }, [token]);
  if (error) return <div className="connect-panel"><h2>Share unavailable</h2><p>{error}</p></div>;
  if (!data) return <div className="empty-state">Opening secure share…</div>;
  return (
    <article className="shared-credential">
      <div className="seal">CITYU<br /><strong>VERIFIED</strong></div>
      <span className="kicker">Privately shared credential</span>
      <h1>{data.credential_type}</h1>
      <p>This credential was issued to</p>
      <h2>{data.student_name}</h2>
      <dl><div><dt>Email</dt><dd>{data.student_email}</dd></div><div><dt>Token ID</dt><dd>#{data.token_id}</dd></div><div><dt>Issuer</dt><dd>{shortWallet(data.issuer_wallet)}</dd></div><div><dt>Status</dt><dd>{data.revoked ? "Revoked" : "Valid"}</dd></div></dl>
    </article>
  );
}
