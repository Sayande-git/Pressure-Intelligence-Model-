import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import { useData } from "./lib/api";
import Overview from "./pages/Overview";
import DataIntel from "./pages/DataIntel";
import Eligibility from "./pages/Eligibility";
import Pressure from "./pages/Pressure";
import Discipline from "./pages/Discipline";
import Venues from "./pages/Venues";
import Rankings from "./pages/Rankings";
import Evidence from "./pages/Evidence";
import Validation from "./pages/Validation";
import Methodology from "./pages/Methodology";
import Reports from "./pages/Reports";

const NAV = [
  ["/", "Executive Overview", "01"], ["/data", "Data Intelligence", "02"], ["/eligibility", "Domestic Player Eligibility", "03"],
  ["/pressure", "Pressure Intelligence", "04"], ["/batting", "Batting Analytics", "05"], ["/bowling", "Bowling Analytics", "06"],
  ["/venues", "Venue Intelligence", "07"], ["/rankings", "Player Rankings", "08"], ["/evidence", "Evidence Centre", "09"],
  ["/validation", "Validation Centre", "10"], ["/methodology", "Methodology", "11"], ["/reports", "Reports & Exports", "12"],
];

const Sidebar = () => {
  const ov = useData("overview");
  return (
    <aside className="lg:fixed lg:inset-y-0 lg:left-0 lg:w-64 border-b lg:border-b-0 lg:border-r border-[var(--line)] bg-[#090C14] z-40 flex flex-col" data-testid="sidebar">
      <div className="px-5 py-5 border-b border-[var(--line)]">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-sm bg-[var(--purple-deep)] border border-[var(--gold)]/60 grid place-items-center font-display text-[var(--gold)] text-sm">RR</div>
          <div>
            <div className="font-display text-lg leading-none text-white">PRESSURE INTEL</div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-[var(--muted)] mt-1">SupeRR Selector · R1</div>
          </div>
        </div>
      </div>
      <nav className="flex lg:flex-col overflow-x-auto lg:overflow-y-auto py-2 flex-1">
        {NAV.map(([to, label, n]) => (
          <NavLink key={to} to={to} end={to === "/"} data-testid={`nav-${to === "/" ? "overview" : to.slice(1)}`}
            className={({ isActive }) => `flex items-center gap-3 px-5 py-2 text-[13px] whitespace-nowrap border-l-2 transition-colors duration-150 ${isActive ? "border-[var(--gold)] text-white bg-[var(--purple-deep)]/25" : "border-transparent text-[var(--muted)] hover:text-white"}`}>
            <span className="num text-[10px] text-[var(--muted)]">{n}</span>{label}
          </NavLink>
        ))}
      </nav>
      <div className="hidden lg:block px-5 py-4 border-t border-[var(--line)] text-[11px] text-[var(--muted)]" data-testid="sidebar-version">
        Dataset version<div className="num text-[var(--gold)] text-xs mt-1">{ov.data?.version || "…"}</div>
      </div>
    </aside>
  );
};

export default function App() {
  return (
    <BrowserRouter>
      <div className="grain min-h-screen">
        <Sidebar />
        <main className="lg:pl-64">
          <div className="max-w-[1500px] mx-auto px-5 sm:px-8 lg:px-12 py-10">
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/data" element={<DataIntel />} />
              <Route path="/eligibility" element={<Eligibility />} />
              <Route path="/pressure" element={<Pressure />} />
              <Route path="/batting" element={<Discipline key="batting" disc="batting" />} />
              <Route path="/bowling" element={<Discipline key="bowling" disc="bowling" />} />
              <Route path="/venues" element={<Venues />} />
              <Route path="/rankings" element={<Rankings />} />
              <Route path="/evidence" element={<Evidence />} />
              <Route path="/validation" element={<Validation />} />
              <Route path="/methodology" element={<Methodology />} />
              <Route path="/reports" element={<Reports />} />
            </Routes>
          </div>
        </main>
        <Toaster theme="dark" />
      </div>
    </BrowserRouter>
  );
}
