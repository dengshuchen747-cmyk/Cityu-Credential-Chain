import { AdminDashboard } from "@/components/admin-dashboard";

export default function SchoolAdminPage() {
  return (
    <section className="page-shell">
      <div className="page-intro">
        <span className="kicker">CityU administrator</span>
        <h1>Control who can create and issue activities.</h1>
        <p>Role changes are signed by your MetaMask administrator wallet and enforced directly by the deployed Sepolia contract.</p>
      </div>
      <AdminDashboard />
    </section>
  );
}
