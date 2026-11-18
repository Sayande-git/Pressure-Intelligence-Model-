import { useMemo, useState } from "react";
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis, Bar, BarChart, Legend } from "recharts";
import { Badge, Btn, DataTable, Loading, PageHeader, Panel } from "../components/kit";
import PlayerProfile from "../components/PlayerProfile";
import { fmt, int, useData } from "../lib/api";
import { AX, TT } from "./Pressure";

export const rankCols = (bat) => [
  { key: "rank", label: "#", num: true },
  { key: "name", label: "Player", render: (r) => <span className="text-white">{r.name}</span> },
  { key: "role", label: "Role", render: (r) => <span className="text-xs">{r.role}</span> },
  { key: "rating", label: "Rating", num: true, render: (r) => <span className={bat ? "text-[var(--purple)]" : "text-[var(--gold)]"}>{fmt(r.rating)}</span> },
  ...(bat
    ? [{ key: "normal_sr", label: "Normal R-B (SR)", num: true, render: (r) => `${int(r.normal_runs)}-${int(r.normal_balls)} (${fmt(r.normal_sr)})` },
       { key: "pressure_sr", label: "Pressure R-B (SR)", num: true, render: (r) => `${int(r.pressure_runs)}-${int(r.pressure_balls)} (${fmt(r.pressure_sr)})` },
       { key: "pressure_avg", label: "Press avg", num: true, render: (r) => fmt(r.pressure_avg) }]
    : [{ key: "normal_econ", label: "Normal econ (W)", num: true, render: (r) => `${fmt(r.normal_econ, 2)} (${int(r.normal_wkts)})` },
       { key: "pressure_econ", label: "Pressure econ (W)", num: true, render: (r) => `${fmt(r.pressure_econ, 2)} (${int(r.pressure_wkts)})` },
       { key: "pressure_dot_pct", label: "Press dot %", num: true, render: (r) => fmt(r.pressure_dot_pct) }]),
  { key: "baseline", label: "Baseline RV", num: true, render: (r) => fmt(r.baseline) },
  { key: "quality", label: "Q", num: true, render: (r) => fmt(r.quality) },
  { key: "delta", label: "D", num: true, render: (r) => <span className={r.delta >= 0 ? "text-emerald-300" : "text-red-300"}>{fmt(r.delta)}</span> },
  { key: "consistency", label: "C", num: true, render: (r) => fmt(r.consistency, 2) },
  { key: "press_balls", label: "Sample", num: true, render: (r) => int(r.press_balls) },
  { key: "boot_top10_pct", label: "Boot top-10 %", num: true, render: (r) => fmt(r.boot_top10_pct, 0) },
  { key: "flags", label: "Flags", text: (r) => (r.capped_in_data ? "capped" : "unverified"), render: (r) => <span className="flex gap-1">{r.robust && <Badge tone="Robust">Robust</Badge>}<Badge tone={r.capped_in_data ? "Ineligible" : "Unverified"}>{r.capped_in_data ? "T20I cap" : "Unverified"}</Badge></span> },
];

export default function Discipline({ disc }) {
  const q = useData(disc);
  const bat = disc === "batting";
  const [sel, setSel] = useState(null);
  const [role, setRole] = useState("All");
  return (
    <Loading q={q}>
      {(d) => {
        const roles = ["All", ...new Set(d.ranking.map((r) => r.role))];
        const rows = d.ranking.filter((r) => role === "All" || r.role === role);
        const cur = sel && d.ranking.find((r) => r.player_id === sel);
        const roleAgg = Object.values(d.ranking.reduce((a, r) => { (a[r.role] ||= { role: r.role, n: 0, q: 0, b: 0 }); a[r.role].n++; a[r.role].q += r.quality; a[r.role].b += r.baseline; return a; }, {}))
          .map((x) => ({ role: x.role, players: x.n, pressure: +(x.q / x.n).toFixed(2), baseline: +(x.b / x.n).toFixed(2) }));
        return (
          <>
            <PageHeader kicker={bat ? "Domain One" : "Domain Two"} title={bat ? "Batting Pressure Intelligence" : "Bowling Pressure Intelligence"} testid={`${disc}-header`}>
              {cur && <Btn testid={`${disc}-back`} onClick={() => setSel(null)}>← All {bat ? "batters" : "bowlers"}</Btn>}
            </PageHeader>
            {cur ? <PlayerProfile r={cur} profile={d.profiles[String(cur.player_id)]} disc={disc} meta={d.meta} /> : (
              <>
                <div className="grid lg:grid-cols-2 gap-6 mb-6">
                  <Panel title="Pressure vs normal baseline" note="shrunk RV per 100 · bubble = sample" testid={`${disc}-scatter`}>
                    <ResponsiveContainer width="100%" height={300}>
                      <ScatterChart margin={{ left: 0, right: 10 }}>
                        <CartesianGrid stroke="#1A2234" /><XAxis type="number" dataKey="baseline" name="Baseline" {...AX} /><YAxis type="number" dataKey="quality" name="Pressure Q" {...AX} />
                        <ZAxis dataKey="press_balls" range={[20, 260]} name="Sample" />
                        <Tooltip {...TT} formatter={(v) => fmt(v, 2)} labelFormatter={() => ""} content={({ payload }) => payload?.[0] ? <div className="panel p-2 text-xs"><b>{payload[0].payload.name}</b><br />Q {fmt(payload[0].payload.quality)} · base {fmt(payload[0].payload.baseline)} · n {int(payload[0].payload.press_balls)}</div> : null} />
                        <Scatter data={d.ranking.slice(10)} fill="#3A4560" onClick={(p) => setSel(p.player_id)} />
                        <Scatter data={d.ranking.slice(0, 10)} fill={bat ? "#8B5CF6" : "#D4AF37"} onClick={(p) => setSel(p.player_id)} />
                      </ScatterChart>
                    </ResponsiveContainer>
                  </Panel>
                  <Panel title="Role-based comparison" note="mean of qualified players" testid={`${disc}-roles`}>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={roleAgg}><CartesianGrid stroke="#1A2234" vertical={false} /><XAxis dataKey="role" {...AX} tick={{ fontSize: 10 }} /><YAxis {...AX} /><Tooltip {...TT} /><Legend wrapperStyle={{ fontSize: 11 }} />
                        <Bar dataKey="baseline" name="Normal RV/100" fill="#3A4560" /><Bar dataKey="pressure" name="Pressure RV/100" fill={bat ? "#8B5CF6" : "#D4AF37"} /></BarChart>
                    </ResponsiveContainer>
                  </Panel>
                </div>
                <Panel title={`Qualified ${bat ? "batters" : "bowlers"} (${d.meta.n_qualified})`} note={`min ${d.meta.n_min_pressure_balls} pressure ${bat ? "balls" : "deliveries"} · ≥${d.meta.min_pressure_innings} pressure innings · click a row for full profile`}>
                  <DataTable testid={`${disc}-table`} rows={rows} cols={rankCols(bat)} onRow={(r) => setSel(r.player_id)} csvName={`${disc}_ratings.csv`}
                    filters={<select data-testid={`${disc}-role-filter`} value={role} onChange={(e) => setRole(e.target.value)} className="bg-[var(--bg)] border border-[var(--line)] rounded-sm text-xs px-2 py-1.5">{roles.map((x) => <option key={x}>{x}</option>)}</select>} />
                </Panel>
              </>
            )}
          </>
        );
      }}
    </Loading>
  );
}
