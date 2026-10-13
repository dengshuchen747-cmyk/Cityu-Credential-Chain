import { StudentDashboard } from "@/components/student-dashboard";

export default function StudentPage() {
  return (
    <section className="page-shell">
      <div className="page-intro"><span className="kicker">Student portal</span><h1>One wallet for every CityU achievement.</h1><p>Track applications and see every non-transferable credential owned by your connected wallet.</p></div>
      <StudentDashboard />
    </section>
  );
}
