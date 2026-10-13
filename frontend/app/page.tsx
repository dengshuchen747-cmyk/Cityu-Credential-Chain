import Link from "next/link";
import { CampaignBrowser } from "@/components/campaign-browser";

export default function Home() {
  return (
    <>
      <section className="hero-section">
        <div className="hero-copy">
          <span className="kicker light">City University of Hong Kong · Sepolia</span>
          <h1>
            CityU experiences become <em>verifiable proof.</em>
          </h1>
          <p>
            Discover university activities, submit participation evidence, and receive
            non-transferable credentials in your own wallet.
          </p>
          <div className="hero-actions">
            <Link className="primary-button light-button" href="#campaigns">
              Explore activities
            </Link>
            <Link className="secondary-button" href="/student">
              Open student wallet
            </Link>
          </div>
          <div className="trust-row">
            <span><b>01</b> CityU issued</span>
            <span><b>02</b> Student owned</span>
            <span><b>03</b> Publicly readable</span>
          </div>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="chain chain-one" />
          <div className="chain chain-two" />
          <div className="credential-card-back" />
          <div className="credential-card-demo">
            <div className="demo-top">
              <span className="brand-mark inverse">C</span>
              <span>CityU<br />Credential</span>
              <small>2026</small>
            </div>
            <div className="demo-center">
              <span>SOULBOUND CREDENTIAL</span>
              <strong>Student<br />Experience</strong>
            </div>
            <div className="demo-bottom">
              <span>NON-TRANSFERABLE</span>
              <span className="demo-qr">▦</span>
            </div>
          </div>
          <div className="verified-stamp">✓<span>VERIFIED<br />ON-CHAIN</span></div>
        </div>
      </section>

      <section className="workflow-strip">
        <div><span>For students</span><strong>Join and earn</strong><p>Choose a CityU activity, submit evidence and receive an SBT after approval.</p></div>
        <div><span>For school</span><strong>Create and issue</strong><p>Authorized creators publish campaigns, review claims and sign credentials.</p></div>
        <div><span>For enterprises</span><strong>Read verified experience</strong><p>Enter a student wallet to inspect all public CityU credentials.</p></div>
      </section>

      <section className="content-section" id="campaigns">
        <div className="section-heading">
          <div><span className="kicker">CityU opportunities</span><h2>Published university activities.</h2></div>
          <p>Every approved activity can become a credential that cannot be transferred, sold or quietly altered.</p>
        </div>
        <CampaignBrowser />
      </section>

      <section className="privacy-section">
        <div><span className="kicker light">Public proof, private evidence</span><h2>Employers see achievements—not application files.</h2></div>
        <div className="privacy-points">
          <p><strong>Public</strong><span>Activity, credential type, issuer, token ID, date and revocation state.</span></p>
          <p><strong>Private</strong><span>Name, email, review notes and evidence files remain in FastAPI storage.</span></p>
          <p><strong>Read-only</strong><span>Only authorized CityU wallets can issue or revoke credentials.</span></p>
        </div>
      </section>
    </>
  );
}
