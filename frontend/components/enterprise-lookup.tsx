"use client";

import { FormEvent, useState } from "react";
import { apiFetch, shortWallet } from "@/lib/api";
import type { StudentCredentialPortfolio } from "@/lib/types";

const EXPLORER = process.env.NEXT_PUBLIC_SEPOLIA_EXPLORER ?? "https://sepolia.etherscan.io";

export function EnterpriseLookup() {
  const [portfolio, setPortfolio] = useState<StudentCredentialPortfolio | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const wallet = String(form.get("wallet") ?? "").trim();
    setLoading(true);
    setError("");
    setSearched(false);
    try {
      const result = await apiFetch<StudentCredentialPortfolio>(
        `/public/students/${wallet}/credentials`,
      );
      setPortfolio(result);
      setSearched(true);
    } catch (reason) {
      setPortfolio(null);
      setError(reason instanceof Error ? reason.message : "Wallet lookup failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="enterprise-layout">
      <section className="verify-card enterprise-search-card">
        <span className="kicker">Public wallet lookup</span>
        <h2>Student wallet address</h2>
        <p>No account or student approval is required. This page only exposes public credential facts—not evidence files or contact details.</p>
        <form className="stack-form" onSubmit={search}>
          <label>
            Ethereum wallet
            <input
              name="wallet"
              required
              placeholder="0x…"
              pattern="0x[a-fA-F0-9]{40}"
              autoComplete="off"
            />
          </label>
          <button className="primary-button" disabled={loading}>
            {loading ? "Checking CityU records…" : "View verified experience"}
          </button>
        </form>
        {error ? <div className="notice error">{error}</div> : null}
      </section>

      <section className="enterprise-results">
        {!searched ? (
          <div className="verification-result enterprise-placeholder">
            <div className="scan-lines" />
            <span className="kicker light">Ready to inspect</span>
            <h2>A verified CityU experience portfolio will appear here.</h2>
            <p>Every result is read-only and tied to the wallet that owns the non-transferable SBT.</p>
          </div>
        ) : null}

        {searched && portfolio ? (
          <>
            <div className="portfolio-summary">
              <div><span className="kicker">Student credential wallet</span><h2>{shortWallet(portfolio.student_wallet)}</h2></div>
              <div><strong>{portfolio.credentials.length}</strong><span>CityU SBTs</span></div>
            </div>
            <div className="credential-list enterprise-credential-list">
              {portfolio.credentials.map((credential) => (
                <article className="portfolio-card" key={credential.token_id}>
                  <div className="portfolio-card-head">
                    <div>
                      <span className="pill">{credential.credential_type}</span>
                      <h3>{credential.campaign_title}</h3>
                    </div>
                    <span className={`status-badge ${credential.valid ? "issued" : "rejected"}`}>
                      {credential.revoked ? "Revoked" : credential.valid ? "Verified" : "Unverified"}
                    </span>
                  </div>
                  <p>{credential.campaign_description}</p>
                  <dl className="credential-facts">
                    <div><dt>Token</dt><dd>#{credential.token_id}</dd></div>
                    <div><dt>Issuer</dt><dd>{shortWallet(credential.issuer_wallet)}</dd></div>
                    <div><dt>Issued</dt><dd>{credential.issued_at ? new Date(credential.issued_at).toLocaleDateString() : "Unknown"}</dd></div>
                    <div><dt>Source</dt><dd>{credential.chain_available ? "Sepolia live" : "CityU index"}</dd></div>
                  </dl>
                  <a className="small-button" href={`${EXPLORER}/tx/${credential.transaction_hash}`} target="_blank" rel="noreferrer">
                    Inspect on Etherscan ↗
                  </a>
                </article>
              ))}
            </div>
            {!portfolio.credentials.length ? (
              <div className="empty-state">No CityU credentials are indexed for this wallet.</div>
            ) : null}
          </>
        ) : null}
      </section>
    </div>
  );
}
