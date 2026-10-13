import Link from "next/link";

export default function SchoolPage() {
  return (
    <section className="page-shell">
      <div className="page-intro">
        <span className="kicker">CityU school portal</span>
        <h1>Choose your responsibility.</h1>
        <p>Selecting a workspace does not grant permission. The connected wallet must hold the corresponding role in the CityU credential contract.</p>
      </div>
      <div className="role-choice-grid">
        <Link className="role-choice-card admin-choice" href="/school/admin">
          <span className="role-number">01</span>
          <span className="kicker">Contract governance</span>
          <h2>Administrator</h2>
          <p>Grant or revoke activity creator permission using the contract’s DEFAULT_ADMIN_ROLE.</p>
          <strong>Manage creators →</strong>
        </Link>
        <Link className="role-choice-card creator-choice" href="/school/creator">
          <span className="role-number">02</span>
          <span className="kicker">Campaign operations</span>
          <h2>Activity creator</h2>
          <p>Publish activities, review student evidence, issue SBTs and manage their lifecycle.</p>
          <strong>Open creator desk →</strong>
        </Link>
      </div>
    </section>
  );
}
