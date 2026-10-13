import { IssuerDashboard } from "@/components/issuer-dashboard";

export default function ActivityCreatorPage() {
  return (
    <section className="page-shell">
      <div className="page-intro">
        <span className="kicker">Activity creator</span>
        <h1>From CityU campaign to student credential.</h1>
        <p>Manage the private evidence workflow in FastAPI, then sign final issuance and revocation transactions with MetaMask.</p>
      </div>
      <IssuerDashboard />
    </section>
  );
}
