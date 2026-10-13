"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiFetch, shortWallet } from "@/lib/api";
import type { IssuerRolePreparation, IssuerRoleRecord } from "@/lib/types";
import { useWallet } from "@/components/wallet-provider";

const EXPLORER = process.env.NEXT_PUBLIC_SEPOLIA_EXPLORER ?? "https://sepolia.etherscan.io";

export function AdminDashboard() {
  const { token, isAdmin, connectAndSignIn, sendTransaction } = useWallet();
  const [issuers, setIssuers] = useState<IssuerRoleRecord[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState("");

  const refresh = useCallback(() => {
    if (!token || !isAdmin) return;
    apiFetch<IssuerRoleRecord[]>("/admin/issuers", {}, token)
      .then(setIssuers)
      .catch((reason: Error) => setMessage(reason.message));
  }, [token, isAdmin]);

  useEffect(refresh, [refresh]);

  async function changeRole(
    action: "grant" | "revoke",
    walletAddress: string,
    label: string,
  ) {
    const key = `${action}-${walletAddress}`;
    setBusy(key);
    setMessage("");
    try {
      const prepared = await apiFetch<IssuerRolePreparation>(
        "/admin/issuers/prepare",
        {
          method: "POST",
          body: JSON.stringify({ wallet_address: walletAddress, label, action }),
        },
        token,
      );
      const transactionHash = await sendTransaction(prepared.transaction);
      setMessage("Role transaction submitted. Waiting for Sepolia confirmation…");
      await apiFetch<IssuerRoleRecord>(
        "/admin/issuers/confirm",
        {
          method: "POST",
          body: JSON.stringify({
            wallet_address: walletAddress,
            label,
            action,
            transaction_hash: transactionHash,
          }),
        },
        token,
      );
      setMessage(
        action === "grant"
          ? "Activity creator permission granted. The creator should sign in again."
          : "Activity creator permission revoked.",
      );
      refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Role update failed");
    } finally {
      setBusy("");
    }
  }

  async function grant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const walletAddress = String(form.get("wallet_address") ?? "").trim();
    const label = String(form.get("label") ?? "").trim();
    await changeRole("grant", walletAddress, label);
    formElement.reset();
  }

  if (!token || !isAdmin) {
    return (
      <div className="connect-panel">
        <span className="kicker">Contract governance</span>
        <h2>Administrator wallet required</h2>
        <p>Connect the wallet that received DEFAULT_ADMIN_ROLE when UniCredentialSBT was deployed.</p>
        <button
          className="primary-button"
          onClick={() => connectAndSignIn().catch((reason) => setMessage(reason.message))}
        >
          Connect administrator wallet
        </button>
        {token && !isAdmin ? <div className="notice error">This wallet is signed in but does not have the administrator role.</div> : null}
        {message ? <div className="form-message">{message}</div> : null}
      </div>
    );
  }

  return (
    <div className="admin-layout">
      <section className="form-panel">
        <span className="kicker">New activity creator</span>
        <h2>Grant issuer permission</h2>
        <p className="panel-copy">This sends an on-chain `grantRole` transaction from your connected MetaMask administrator account.</p>
        <form className="stack-form" onSubmit={grant}>
          <label>
            Creator or department name
            <input name="label" placeholder="School of Computing" maxLength={120} />
          </label>
          <label>
            Creator wallet address
            <input name="wallet_address" required placeholder="0x…" pattern="0x[a-fA-F0-9]{40}" />
          </label>
          <button className="primary-button" disabled={Boolean(busy)}>
            {busy.startsWith("grant-") ? "Confirming…" : "Grant ISSUER_ROLE"}
          </button>
        </form>
      </section>

      <section className="data-panel">
        <div className="section-heading compact">
          <div><span className="kicker">Permission registry</span><h2>Activity creators</h2></div>
        </div>
        {issuers.map((issuer) => (
          <div className="issuer-role-row" key={issuer.wallet_address}>
            <div>
              <strong>{issuer.label}</strong>
              <code title={issuer.wallet_address}>{shortWallet(issuer.wallet_address)}</code>
              {issuer.transaction_hash ? (
                <a href={`${EXPLORER}/tx/${issuer.transaction_hash}`} target="_blank" rel="noreferrer">Last role transaction ↗</a>
              ) : null}
            </div>
            <span className={`status-badge ${issuer.active ? "issued" : "rejected"}`}>
              {issuer.active ? "Authorized" : "Revoked"}
            </span>
            {issuer.active ? (
              <button
                className="small-button danger"
                disabled={Boolean(busy)}
                onClick={() => changeRole("revoke", issuer.wallet_address, issuer.label)}
              >
                {busy === `revoke-${issuer.wallet_address}` ? "Confirming…" : "Revoke"}
              </button>
            ) : (
              <button
                className="small-button"
                disabled={Boolean(busy)}
                onClick={() => changeRole("grant", issuer.wallet_address, issuer.label)}
              >
                {busy === `grant-${issuer.wallet_address}` ? "Confirming…" : "Restore"}
              </button>
            )}
          </div>
        ))}
        {!issuers.length ? <div className="empty-state">No creator role changes have been recorded yet.</div> : null}
        {message ? <div className="form-message">{message}</div> : null}
      </section>
    </div>
  );
}
