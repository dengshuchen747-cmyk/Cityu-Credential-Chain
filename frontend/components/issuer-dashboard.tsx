"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import type {
  Campaign,
  Claim,
  Credential,
  CredentialIssuePreparation,
  CredentialRevokePreparation,
} from "@/lib/types";
import { useWallet } from "@/components/wallet-provider";

export function IssuerDashboard() {
  const { token, isIssuer, connectAndSignIn, sendTransaction } = useWallet();
  const [claims, setClaims] = useState<Claim[]>([]);
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [busyAction, setBusyAction] = useState("");

  const refresh = useCallback(() => {
    if (!token || !isIssuer) return;
    Promise.all([
      apiFetch<Claim[]>("/issuer/claims", {}, token),
      apiFetch<Credential[]>("/issuer/credentials", {}, token),
    ])
      .then(([claimData, credentialData]) => {
        setClaims(claimData);
        setCredentials(credentialData);
      })
      .catch((reason: Error) => setMessage(reason.message));
  }, [token, isIssuer]);

  useEffect(refresh, [refresh]);

  async function createCampaign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    setBusy(true);
    try {
      const form = new FormData(formElement);
      const campaign = await apiFetch<Campaign>(
        "/campaigns",
        {
          method: "POST",
          body: JSON.stringify({
            title: form.get("title"),
            description: form.get("description"),
            credential_type: form.get("credential_type"),
            max_claims: form.get("max_claims") ? Number(form.get("max_claims")) : null,
            metadata_uri: form.get("metadata_uri"),
          }),
        },
        token,
      );
      setMessage(`Campaign “${campaign.title}” was published.`);
      formElement.reset();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not create campaign");
    } finally {
      setBusy(false);
    }
  }

  async function review(claimId: number, status: "approved" | "rejected") {
    try {
      await apiFetch(
        `/issuer/claims/${claimId}/review`,
        {
          method: "POST",
          body: JSON.stringify({ status, note: "Reviewed in activity creator dashboard" }),
        },
        token,
      );
      refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Review failed");
    }
  }

  async function issue(claimId: number) {
    setBusyAction(`issue-${claimId}`);
    try {
      const prepared = await apiFetch<CredentialIssuePreparation>(
        `/issuer/claims/${claimId}/issue/prepare`,
        { method: "POST" },
        token,
      );
      const transactionHash = await sendTransaction(prepared.transaction);
      setMessage("Issuance submitted to Sepolia. Waiting for confirmation…");
      const credential = await apiFetch<Credential>(
        `/issuer/claims/${claimId}/issue/confirm`,
        { method: "POST", body: JSON.stringify({ transaction_hash: transactionHash }) },
        token,
      );
      setMessage(`Credential #${credential.token_id} was issued successfully.`);
      refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Issuance failed");
    } finally {
      setBusyAction("");
    }
  }

  async function revoke(tokenId: number) {
    const reason = prompt("Revocation reason");
    if (!reason) return;
    setBusyAction(`revoke-${tokenId}`);
    try {
      const prepared = await apiFetch<CredentialRevokePreparation>(
        `/issuer/credentials/${tokenId}/revoke/prepare`,
        { method: "POST", body: JSON.stringify({ reason }) },
        token,
      );
      const transactionHash = await sendTransaction(prepared.transaction);
      setMessage("Revocation submitted to Sepolia. Waiting for confirmation…");
      await apiFetch<Credential>(
        `/issuer/credentials/${tokenId}/revoke/confirm`,
        {
          method: "POST",
          body: JSON.stringify({ reason, transaction_hash: transactionHash }),
        },
        token,
      );
      setMessage(`Credential #${tokenId} was revoked.`);
      refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Revocation failed");
    } finally {
      setBusyAction("");
    }
  }

  if (!token || !isIssuer) {
    return (
      <div className="connect-panel">
        <span className="kicker">Restricted workspace</span>
        <h2>Activity creator authorization required</h2>
        <p>Connect a wallet that the CityU contract administrator has granted ISSUER_ROLE.</p>
        <button
          className="primary-button"
          onClick={() => connectAndSignIn().catch((reason) => setMessage(reason.message))}
        >
          Connect creator wallet
        </button>
        {message ? <div className="form-message">{message}</div> : null}
      </div>
    );
  }

  return (
    <div className="issuer-layout">
      <section className="form-panel">
        <span className="kicker">Campaign studio</span>
        <h2>Create a CityU activity</h2>
        <form className="stack-form" onSubmit={createCampaign}>
          <label>Campaign title<input name="title" required minLength={3} /></label>
          <label>Credential type<input name="credential_type" required placeholder="Workshop Completion" /></label>
          <label>Description<textarea name="description" required minLength={10} rows={4} /></label>
          <div className="field-pair">
            <label>Maximum claims<input name="max_claims" type="number" min={1} /></label>
            <label>Public IPFS metadata URI<input name="metadata_uri" placeholder="ipfs://…" /></label>
          </div>
          <button className="primary-button" disabled={busy}>{busy ? "Publishing…" : "Publish campaign"}</button>
        </form>
      </section>
      <section className="data-panel">
        <div className="section-heading compact"><div><span className="kicker">Review queue</span><h2>Student claims</h2></div></div>
        {claims.map((claim) => (
          <div className="review-card" key={claim.id}>
            <div><strong>{claim.student_name}</strong><span>{claim.student_email}</span><code>{claim.evidence_hash}</code></div>
            <span className={`status-badge ${claim.status}`}>{claim.status}</span>
            <div className="review-actions">
              {claim.status === "pending" ? (
                <>
                  <button onClick={() => review(claim.id, "approved")}>Approve</button>
                  <button className="ghost" onClick={() => review(claim.id, "rejected")}>Reject</button>
                </>
              ) : null}
              {claim.status === "approved" ? (
                <button disabled={Boolean(busyAction)} onClick={() => issue(claim.id)}>
                  {busyAction === `issue-${claim.id}` ? "Confirming…" : "Issue SBT with MetaMask"}
                </button>
              ) : null}
            </div>
          </div>
        ))}
        {!claims.length ? <div className="empty-state">The review queue is empty.</div> : null}

        <div className="section-heading compact credential-heading"><div><span className="kicker">Credential lifecycle</span><h2>Issued credentials</h2></div></div>
        {credentials.map((credential) => (
          <div className="claim-row" key={credential.id}>
            <div><strong>Token #{credential.token_id}</strong><span>{credential.revoked_at ? "Revoked" : "Active"}</span></div>
            {!credential.revoked_at ? (
              <button className="small-button danger" disabled={Boolean(busyAction)} onClick={() => revoke(credential.token_id)}>
                {busyAction === `revoke-${credential.token_id}` ? "Confirming…" : "Revoke"}
              </button>
            ) : null}
          </div>
        ))}
        {!credentials.length ? <div className="empty-state">No credentials issued by this wallet yet.</div> : null}
        {message ? <div className="form-message">{message}</div> : null}
      </section>
    </div>
  );
}
