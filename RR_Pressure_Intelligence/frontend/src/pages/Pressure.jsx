import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from "recharts";
import { Badge, DataTable, Formula, Loading, PageHeader, Panel } from "../components/kit";
import { fmt, int, useData } from "../lib/api";

export const AX = { stroke: "#5A6378", fontSize: 11 };
export const TT = { contentStyle: { background: "#0B0F19", border: "1px solid #222C3F", fontSize: 12 }, cursor: { fill: "rgba(139,92,246,.08)" } };

const Heat = ({ rows, xKey, yKey, testid }) => {
  const xs = [...new Set(rows.map((r) => r[xKey]))];
  const ys = [...new Set(rows.map((r) => r[yKey]))];
  const max = Math.max(...rows.map((r) => r.LI));
  return (
    <div className="overflow-auto" data-testid={testid}>
      <table className="text-xs num">
        <thead><tr><th className="p-1 text-[var(--muted)]">{yKey} \ {xKey}</th>{xs.map((x) => <th key={x} className="p-1 text-[var(--muted)] font-normal">{x}</th>)}</tr></thead>
        <tbody>{ys.map((y) => (
          <tr key={y}><td className="p-1 text-[var(--muted)]">{y}</td>{xs.map((x) => {
            const c = rows.find((r) => r[xKey] === x && r[yKey] === y);
            return <td key={x} className="p-0"><div title={c ? `LI ${c.LI}` : ""} className="w-16 h-8 grid place-items-center m-0.5 rounded-sm" style={{ background: c ? `rgba(139,92,246,${0.1 + 0.85 * (c.LI / max)})` : "transparent" }}>{c ? fmt(c.LI, 2) : ""}</div></td>;
          })}</tr>))}
        </tbody>
      </table>
    </div>
  );
};

export default function Pressure() {
  const q = useData("pressure");
  return (
    <Loading q={q}>
      {(p) => (
        <>
          <PageHeader kicker="Phase 3 · Pressure Definition Engine" title="Pressure Intelligence" testid="pressure-header" />
          <div className="grid lg:grid-cols-5 gap-6 mb-6">
            <Panel title="Definition" className="lg:col-span-3" testid="pressure-definition">
              <div className="space-y-3 text-sm leading-relaxed">
                <p>Each delivery gets a <b className="text-white">Leverage Index (LI)</b>: the swing in the batting side's win probability between its best routine outcome (a boundary) and its worst (a wicket), computed from the <i>pre-ball</i> state only — runs, wickets in hand, legal balls left, target (chases), competition.</p>
                <Formula>{`WP = logistic(f(state))   # separate models: setting (inn 1) and chasing (inn 2)
L(s) = WP(s | +4 runs, 1 ball used) − WP(s | wicket, 1 ball used)
LI   = L / mean(L)
Tier = Normal  if LI < P${p.cutoffs.q_mod * 100} (within innings)
       Moderate if P${p.cutoffs.q_mod * 100} ≤ LI < P${p.cutoffs.q_high * 100}
       High     if LI ≥ P${p.cutoffs.q_high * 100}`}</Formula>
                <p className="text-[var(--muted)]">Required-vs-current rate gap, wickets in hand, balls left, target difficulty and match closeness all act through the WP surface instead of arbitrary hand-set thresholds. The same leverage is zero-sum, so batting and bowling share the situation definition but use separate tier cut-offs, separate performance currencies and separate baselines.</p>
              </div>
            </Panel>
            <Panel title="Win-probability model check" note="trained 2022-24, tested 2025-26" className="lg:col-span-2" testid="pressure-wp">
              <div className="grid grid-cols-2 gap-3 mb-4">
                {["innings_1", "innings_2"].map((k) => (
                  <div key={k} className="border border-[var(--line)] rounded-sm p-3">
                    <div className="text-[11px] uppercase text-[var(--muted)]">{k === "innings_1" ? "Setting" : "Chasing"}</div>
                    <div className="num text-xl text-[var(--gold)]">AUC {p.wp_validation[k].auc}</div>
                    <div className="num text-xs text-[var(--muted)]">Brier {p.wp_validation[k].brier} · {int(p.wp_validation[k].n_test_deliveries)} balls</div>
                  </div>
                ))}
              </div>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={p.wp_validation.innings_2.calibration.map((c, i) => ({ ...c, set: p.wp_validation.innings_1.calibration[i]?.obs }))}>
                  <CartesianGrid stroke="#1A2234" /><XAxis dataKey="pred" {...AX} /><YAxis {...AX} domain={[0, 1]} /><Tooltip {...TT} /><Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line dataKey="obs" name="Chasing observed" stroke="#8B5CF6" dot={{ r: 2 }} /><Line dataKey="pred" name="Perfect calibration" stroke="#5A6378" strokeDasharray="4 4" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </Panel>
          </div>
          <Panel title="Pressure tiers — league behaviour" className="mb-6" testid="pressure-tiers">
            <DataTable testid="tier-table" search={false} rows={p.tiers.map((t) => ({ ...t, close: p.close_match_pct_by_tier[t.tier] }))} cols={[
              { key: "tier", label: "Tier", render: (r) => <Badge>{r.tier}</Badge> }, { key: "balls", label: "Balls", num: true, render: (r) => int(r.balls) },
              { key: "share", label: "Share", num: true }, { key: "strike_rate", label: "SR", num: true }, { key: "dismissal_pct", label: "Out %", num: true },
              { key: "dot_pct", label: "Dot %", num: true }, { key: "boundary_pct", label: "Boundary %", num: true }, { key: "mean_LI", label: "Mean LI", num: true },
              { key: "pct_death", label: "% death overs", num: true }, { key: "close", label: "% from close finishes", num: true },
            ]} />
            <p className="text-xs text-[var(--muted)] mt-3">Validation: high-tier balls are drawn far more often from matches with close final margins (≤15 runs or ≤3 wickets), and scoring falls as pressure rises — the tiers separate genuinely tense contests, not merely death overs.</p>
          </Panel>
          <div className="grid lg:grid-cols-2 gap-6 mb-6">
            <Panel title="Leverage distribution" testid="pressure-hist">
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={p.li_hist}><CartesianGrid stroke="#1A2234" vertical={false} /><XAxis dataKey="x" {...AX} /><YAxis {...AX} /><Tooltip {...TT} /><Bar dataKey="n" name="Deliveries" fill="#8B5CF6" /></BarChart>
              </ResponsiveContainer>
            </Panel>
            <Panel title="Phase × tier (balls faced)" testid="pressure-phase">
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={p.phase_tier_counts}><CartesianGrid stroke="#1A2234" vertical={false} /><XAxis dataKey="phase" {...AX} /><YAxis {...AX} /><Tooltip {...TT} /><Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="Normal" stackId="a" fill="#3A4560" /><Bar dataKey="Moderate" stackId="a" fill="#8B5CF6" /><Bar dataKey="High" stackId="a" fill="#D4AF37" /></BarChart>
              </ResponsiveContainer>
            </Panel>
          </div>
          <div className="grid lg:grid-cols-2 gap-6 mb-6">
            <Panel title="Chase leverage map" note="mean LI by required rate × balls left"><Heat rows={p.chase_heat} xKey="bl_b" yKey="rrr_b" testid="pressure-chase-heat" /></Panel>
            <Panel title="Wickets × phase leverage" note="mean LI"><Heat rows={p.wicket_phase_heat} xKey="wk_bucket" yKey="phase" testid="pressure-wk-heat" /></Panel>
          </div>
          <Panel title="Real deliveries, scored" note="sampled from the data" testid="pressure-examples">
            <DataTable testid="pressure-example-table" search={false} rows={p.examples} cols={[
              { key: "match_id", label: "Match", num: true }, { key: "match_date", label: "Date" }, { key: "comp_name", label: "Competition" },
              { key: "ov", label: "Ball", render: (r) => `${r.overid}.${r.over_ball_num}` }, { key: "score", label: "Score", render: (r) => `${r.score}/${r.wk}` },
              { key: "req", label: "Req", num: true, render: (r) => fmt(r.req, 0) }, { key: "balls_left", label: "Balls left", num: true },
              { key: "wp_before", label: "WP", num: true, render: (r) => fmt(r.wp_before, 2) }, { key: "LI", label: "LI", num: true, render: (r) => fmt(r.LI, 2) },
              { key: "bat_tier", label: "Tier", render: (r) => <Badge>{r.bat_tier}</Badge> },
            ]} />
          </Panel>
        </>
      )}
    </Loading>
  );
}
