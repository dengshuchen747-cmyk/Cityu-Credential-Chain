"use client";

import { useEffect, useState } from "react";
import { apiFetch, shortWallet } from "@/lib/api";
import type { Claim, StudentCredentialPortfolio } from "@/lib/types";
import { useWallet } from "@/components/wallet-provider";

const EXPLORER = process.env.NEXT_PUBLIC_SEPOLIA_EXPLORER ?? "https://sepolia.etherscan.io";

export function StudentDashboard() {
  const { token, wallet, connectAndSignIn } = useWallet();
  const [claims, setClaims] = useState<Claim[]>([]);
  const [portfolio, setPortfolio] = useState<StudentCredentialPortfolio | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token || !wallet) return;
    Promise.all([
      apiFetch<Claim[]>("/claims/mine", {}, token),
      apiFetch<StudentCredentialPortfolio>(`/public/students/${wallet}/credentials`),
    ])
      .then(([claimData, portfolioData]) => {
        setClaims(claimData);
        setPortfolio(portfolioData);
      })
      .catch((reason: Error) => setError(reason.message));
  }, [token, wallet]);

  if (!token) {
    return (
      <div className="connect-panel">
        <div className="credential-orbit">◎</div>
        <h2>Your credentials begin with your wallet</h2>
        <p>Sign a one-time message to see the SBTs owned by your current MetaMask account.</p>
        <button
          className="primary-button"
          onClick={() => connectAndSignIn().catch((reason) => setError(reason.message))}
        >
          Connect MetaMask
        </button>
        {error ? <div className="form-message">{error}</div> : null}
      </div>
    );
  }

  const credentials = portfolio?.credentials ?? [];
  return (
    <div className="dashboard-grid">
      <aside className="profile-panel">
        <span className="kicker">Student wallet</span>
        <h2>Academic wallet</h2>
        <code>{wallet}</code>
        <div className="profile-stat"><strong>{claims.length}</strong><span>Applications</span></div>
        <div className="profile-stat"><strong>{credentials.length}</strong><span>Owned SBTs</span></div>
      </aside>
      <section className="data-panel">
        <div className="section-heading compact">
          <div><span className="kicker">On-chain portfolio</span><h2>My credentials</h2></div>
        </div>
        <div className="credential-list">
          {credentials.map((credential) => (
            <article className="portfolio-card" key={credential.token_id}>
              <div className="portfolio-card-head">
                <div>
                  <span className="pill">{credential.credential_type}</span>
                  <h3>{credential.campaign_title}</h3>
                </div>
                <span className={`status-badge ${credential.revoked ? "rejected" : "issued"}`}>
                  {credential.revoked ? "Revoked" : "Active"}
                </span>
              </div>
              <p>{credential.campaign_description}</p>
              <dl className="credential-facts">
                <div><dt>Token</dt><dd>#{credential.token_id}</dd></div>
                <div><dt>Issuer</dt><dd>{shortWallet(credential.issuer_wallet)}</dd></div>
                <div><dt>Issued</dt><dd>{credential.issued_at ? new Date(credential.issued_at).toLocaleDateString() : "Pending index"}</dd></div>
                <div><dt>Chain check</dt><dd>{credential.chain_available ? "Sepolia confirmed" : "Local index"}</dd></div>
              </dl>
              <a className="small-button" href={`${EXPLORER}/tx/${credential.transaction_hash}`} target="_blank" rel="noreferrer">
                View transaction ↗
              </a>
            </article>
          ))}
        </div>
        {!credentials.length ? <div className="empty-state">No SBTs are owned by this wallet yet.</div> : null}

        <div className="section-heading compact credential-heading">
          <div><span className="kicker">Application history</span><h2>My claims</h2></div>
        </div>
        {claims.map((claim) => (
          <div className="claim-row" key={claim.id}>
            <div><strong>Campaign #{claim.campaign_id}</strong><span>Submitted {new Date(claim.submitted_at).toLocaleDateString()}</span></div>
            <span className={`status-badge ${claim.status}`}>{claim.status}</span>
          </div>
        ))}
        {!claims.length ? <div className="empty-state">No applications submitted yet.</div> : null}
        {error ? <div className="notice error">{error}</div> : null}
      </section>
    </div>
  );
}
