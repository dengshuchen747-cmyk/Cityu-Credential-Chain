"use client";

import { useEffect, useState } from "react";
import { apiFetch, shortWallet } from "@/lib/api";
import type { Campaign } from "@/lib/types";
import { ClaimDialog } from "@/components/claim-dialog";

export function CampaignBrowser() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selected, setSelected] = useState<Campaign | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch<Campaign[]>("/campaigns")
      .then(setCampaigns)
      .catch((reason: Error) => setError(reason.message));
  }, []);

  if (error) return <div className="notice error">FastAPI is unavailable: {error}</div>;
  return (
    <>
      <div className="campaign-grid">
        {campaigns.map((campaign, index) => (
          <article className="campaign-card" key={campaign.id}>
            <div className={`campaign-visual visual-${index % 4}`}>
              <span>{campaign.credential_type.slice(0, 2).toUpperCase()}</span>
              <small>CityU verified learning</small>
            </div>
            <div className="campaign-body">
              <div className="eyebrow-row">
                <span className="pill">{campaign.credential_type}</span>
                <span className="status-dot">Open</span>
              </div>
              <h3>{campaign.title}</h3>
              <p>{campaign.description}</p>
              <div className="campaign-meta">
                <span>Creator {shortWallet(campaign.issuer_wallet)}</span>
                <span>{campaign.max_claims ? `${campaign.max_claims} places` : "Open quota"}</span>
              </div>
              <button className="text-button" onClick={() => setSelected(campaign)}>
                Submit evidence <span>→</span>
              </button>
            </div>
          </article>
        ))}
      </div>
      {!campaigns.length ? <div className="empty-state">No active campaigns yet.</div> : null}
      {selected ? <ClaimDialog campaign={selected} onClose={() => setSelected(null)} /> : null}
    </>
  );
}
