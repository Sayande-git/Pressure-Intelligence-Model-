import { Formula, Loading, PageHeader, Panel, DataTable } from "../components/kit";
import { useData } from "../lib/api";

const METRICS = [
  ["Leverage Index (LI)", "WP(+4) − WP(wicket) from pre-ball state, ÷ mean", "Measures how much the next ball can swing the match", "Higher = more pressure", "Mean-normalised; tiers by within-innings quantile", "Defines pressure sample & tiers"],
  ["Batting RV per ball", "(runs − v·E[runs|ctx]) − W·(out − P[out|ctx])", "Scoring and survival vs an average batter in the identical situation", "Higher better", "Runs per 100 balls", "Feeds Q, baseline, C"],
  ["Bowling RV per delivery", "(v·E[conc|ctx] − conceded) + W·(wkt − P[wkt|ctx])", "Economy and wicket-taking in one currency", "Higher better", "Runs saved per 100 deliveries", "Feeds Q, baseline, C"],
  ["Wicket value W", "RE(over, w) − RE(over, w+1) from 1st-innings run expectancy", "An early wicket costs more than a last-over wicket", "—", "Clipped 1–25 runs, smoothed", "Weights dismissals"],
  ["Q · pressure quality", "ΣRV_press / (n + k) × 100", "Primary objective: value delivered under pressure", "Higher better", "z-score among qualified", "50%"],
  ["D · rise vs baseline", "Q − ΣRV_normal / (n_n + k_n) × 100", "Compared with own usual level", "Higher better", "z-score", "25%"],
  ["C · consistency", "(succ + 10·league) / (pressure inns + 10)", "Repeated delivery across matches, not one big night", "Higher better", "z-score", "25%"],
  ["Venue factor v", "(venue runs + 600·grp rpb) / ((balls + 600)·grp rpb)", "Scoring environment differs by ground", "—", "Shrunk toward 1.0", "Scales expectations"],
];

export default function Methodology() {
  const b = useData("batting");
  const w = useData("bowling");
  return (
    <Loading q={b}>
      {(bat) => (
        <>
          <PageHeader kicker="Transparent, reproducible" title="Methodology" testid="methodology-header" />
          <Panel title="Metric register" className="mb-6">
            <DataTable testid="metric-register" search={false} rows={METRICS.map(([m, d, j, dir, n, c]) => ({ m, d, j, dir, n, c }))} cols={[
              { key: "m", label: "Metric", render: (r) => <span className="text-white">{r.m}</span> }, { key: "d", label: "Definition", render: (r) => <span className="num text-xs text-[var(--gold)]">{r.d}</span> },
              { key: "j", label: "Cricketing justification", render: (r) => <span className="text-xs whitespace-normal">{r.j}</span> }, { key: "dir", label: "Direction" },
              { key: "n", label: "Normalisation", render: (r) => <span className="text-xs">{r.n}</span> }, { key: "c", label: "Contribution" }]} />
          </Panel>
          <div className="grid lg:grid-cols-2 gap-6 mb-6">
            <Panel title="Final rating">
              <Formula>{`Rating = 50 + 10 × (0.50·z(Q) + 0.25·z(D) + 0.25·z(C))
k (bat) = σ²/τ² = ${bat.meta.k_pressure}   k (bowl) = ${w.data?.meta.k_pressure ?? "…"}
Qualify: n_press ≥ k/4 (reliability ≥ 0.20) and ≥ ${bat.meta.min_pressure_innings} pressure innings
Batting n_min = ${bat.meta.n_min_pressure_balls} balls   Bowling n_min = ${w.data?.meta.n_min_pressure_balls ?? "…"} deliveries`}</Formula>
              <p className="text-sm text-[var(--muted)] mt-3 leading-relaxed">Weights follow the brief's three asks — perform under pressure (Q), relative to usual level (D), consistently (C). They are not tuned to produce a desired list; the Validation Centre shows the Top-10 under 15 alternative weightings, 4 tier definitions and 3 sample thresholds.</p>
            </Panel>
            <Panel title="Data handling rules">
              <ul className="text-sm space-y-2 leading-relaxed">
                <li>Super overs excluded; rain-revised ball limits and targets honoured.</li>
                <li>Legal ball = not wide / no-ball / "other". Batter balls exclude wides only.</li>
                <li>Bowler runs = bat runs + wide/no-ball penalties; byes & leg-byes not charged.</li>
                <li>Bowler wickets: caught, bowled, LBW, stumped, hit wicket. Run-outs credited to the dismissed batter only.</li>
                <li>All state features use cumulative values <i>before</i> each ball — no future-information leakage.</li>
                <li>Batting and bowling are scored by independent models; there is no all-rounder model.</li>
                <li>IPL, T20I and Emerging are separate context cells, so each ball is judged against its own competition's norms.</li>
              </ul>
            </Panel>
          </div>
          <Panel title="Context cells">
            <p className="text-sm leading-relaxed">Expectations E[runs], P[wicket], E[conceded] are computed per cell: <span className="num text-[var(--gold)]">competition group × innings × phase (PP 1-6, Middle 7-15, Death 16-20) × wickets lost (0-1, 2-3, 4-5, 6+) × pressure tier</span>. Because tier is in the cell, a batter's pressure RV is measured against what the league does in equally tense situations — this separates "pressure skill" from "batting in easier phases".</p>
          </Panel>
        </>
      )}
    </Loading>
  );
}
