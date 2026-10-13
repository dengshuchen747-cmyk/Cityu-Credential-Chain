"use client";

import { FormEvent, useState } from "react";
import { apiFetch, shortWallet } from "@/lib/api";
import type { Verification } from "@/lib/types";

export function VerificationForm() {
  const [result, setResult] = useState<Verification | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function verify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setResult(null);
    const form = new FormData(event.currentTarget);
    const tokenId = form.get("token_id");
    const hash = String(form.get("data_hash") ?? "").trim();
    try {
      setResult(await apiFetch<Verification>(`/credentials/${tokenId}${hash ? `?submitted_hash=${encodeURIComponent(hash)}` : ""}`));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Verification failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="verify-layout">
      <form className="verify-card" onSubmit={verify}>
        <span className="kicker">Public verification</span>
        <h2>Check a credential</h2>
        <p>Enter the token ID from the QR code. A data hash is optional for locally indexed credentials.</p>
        <label>Token ID<input name="token_id" type="number" min={1} required placeholder="1" /></label>
        <label>Credential data hash (optional)<input name="data_hash" pattern="0x[a-fA-F0-9]{64}" placeholder="0x…" /></label>
        <button className="primary-button" disabled={busy}>{busy ? "Checking Sepolia…" : "Verify authenticity"}</button>
        {error ? <div className="notice error">{error}</div> : null}
      </form>
      <section className={`verification-result ${result?.valid ? "valid" : result ? "invalid" : "waiting"}`}>
        {result ? (
          <>
            <div className="result-icon">{result.valid ? "✓" : "!"}</div>
            <span className="kicker">{result.chain_available ? "Sepolia result" : "Local development result"}</span>
            <h2>{result.valid ? "Credential is valid" : result.revoked ? "Credential was revoked" : "Credential is invalid"}</h2>
            <dl>
              <div><dt>Token</dt><dd>#{result.token_id}</dd></div>
              <div><dt>Hash match</dt><dd>{result.hash_matches ? "Yes" : "No"}</dd></div>
              <div><dt>Student</dt><dd>{shortWallet(result.student_wallet)}</dd></div>
              <div><dt>Issuer</dt><dd>{shortWallet(result.issuer_wallet)}</dd></div>
              <div><dt>Issued</dt><dd>{result.issued_at ? new Date(result.issued_at).toLocaleString() : "—"}</dd></div>
            </dl>
          </>
        ) : (
          <><div className="scan-lines" /><span className="kicker">Ready to inspect</span><h2>Blockchain proof will appear here</h2><p>The public result never exposes evidence files or student email.</p></>
        )}
      </section>
    </div>
  );
}
