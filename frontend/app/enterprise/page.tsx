import { EnterpriseLookup } from "@/components/enterprise-lookup";

export default function EnterprisePage() {
  return (
    <section className="page-shell enterprise-page">
      <div className="page-intro">
        <span className="kicker">Enterprise verification</span>
        <h1>See the truth behind a student wallet.</h1>
        <p>Enter a wallet address to view all CityU SBT experiences and their current on-chain validity. No login is required.</p>
      </div>
      <EnterpriseLookup />
    </section>
  );
}
