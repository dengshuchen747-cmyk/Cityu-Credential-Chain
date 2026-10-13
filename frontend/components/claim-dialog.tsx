"use client";

import { FormEvent, useState } from "react";
import { apiFetch } from "@/lib/api";
import type { Campaign, Claim } from "@/lib/types";
import { useWallet } from "@/components/wallet-provider";

export function ClaimDialog({ campaign, onClose }: { campaign: Campaign; onClose: () => void }) {
  const { token, wallet, connectAndSignIn } = useWallet();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    if (!token) {
      try {
        await connectAndSignIn();
        setMessage("Wallet connected. Submit the form once more.");
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Wallet login failed");
      }
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const formData = new FormData(formElement);
      const claim = await apiFetch<Claim>(
        `/campaigns/${campaign.id}/claims`,
        { method: "POST", body: formData },
        token,
      );
      setMessage(`Application #${claim.id} submitted successfully.`);
      formElement.reset();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Submission failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <section className="modal-card" onMouseDown={(event) => event.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close">×</button>
        <span className="kicker">Credential application</span>
        <h2>{campaign.title}</h2>
        <p>Evidence stays private. Only a cryptographic fingerprint becomes part of the final credential proof.</p>
        <form className="stack-form" onSubmit={submit}>
          <label>
            Full name
            <input name="student_name" required minLength={2} />
          </label>
          <label>
            CityU email
            <input name="student_email" type="email" required />
          </label>
          <label>
            Evidence (PDF, JPG or PNG)
            <input name="evidence" type="file" accept=".pdf,.jpg,.jpeg,.png" required />
          </label>
          <div className="wallet-line">Recipient wallet: {wallet || "Connect MetaMask to continue"}</div>
          <button className="primary-button" disabled={busy} type="submit">
            {busy ? "Submitting…" : token ? "Submit application" : "Connect wallet"}
          </button>
          {message ? <div className="form-message">{message}</div> : null}
        </form>
      </section>
    </div>
  );
}
