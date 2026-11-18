import { useState } from "react";
import { CartesianGrid, ErrorBar, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { Btn, DataTable, KV, Loading, PageHeader, Panel } from "../components/kit";
import { fmt, int, useData } from "../lib/api";
import { AX, TT } from "./Pressure";

export default function Validation() {
  const [disc, setDisc] = useState("batting");
  const q = useData(disc);
  return (
    <Loading q={q}>
      {(d) => {
        const top = d.ranking.slice(0, 15).map((r, i) => ({ ...r, y: i + 1, err: [r.boot_median_rank - r.boot_rank_p05, r.boot_rank_p95 - r.boot_median_rank] }));
        const g = d.weight_grid;
        return (
          <>
            <PageHeader kicker="Phase 7 · Robustness" title="Validation Centre" testid="validation-header">
              <Btn testid="val-bat" active={disc === "batting"} onClick={() => setDisc("batting")}>Batting</Btn>
              <Btn testid="val-bowl" active={disc === "bowling"} onClick={() => setDisc("bowling")}>Bowling</Btn>
            </PageHeader>
            <div className="grid lg:grid-cols-3 gap-6 mb-6">
              <Panel title="Sample reliability" testid="val-reliability">
                <KV rows={[["σ² per-ball RV", d.meta.sigma2], ["τ² between players", d.meta.tau2], ["k = σ²/τ²", d.meta.k_pressure], ["Min pressure sample (rel ≥ 0.20)", d.meta.n_min_pressure_balls], ["Min pressure innings", d.meta.min_pressure_innings], ["Qualified", d.meta.n_qualified]]} />
              </Panel>
              <Panel title="Temporal out-of-sample" note="2022-24 vs 2025-26" testid="val-temporal">
                <KV rows={[["Players (≥60 pressure balls each era)", d.temporal.players], ["Pearson r", d.temporal.pearson_r], ["Spearman ρ", d.temporal.spearman_r]]} />
                <p className="text-xs text-[var(--muted)] mt-3">A modest positive correlation means pressure performance is partly repeatable — which is exactly why shrinkage and consistency matter more than one hot season.</p>
              </Panel>
              <Panel title="Venue adjustment effect" testid="val-venue">
                <KV rows={[["Top-10 overlap (adjusted vs raw)", `${d.venue_adjust_effect.top10_overlap}/10`], ["Spearman", d.venue_adjust_effect.spearman]]} />
                <p className="text-xs text-[var(--muted)] mt-3">Venue context refines but does not override the pressure objective.</p>
              </Panel>
            </div>
            <Panel title="Bootstrap rank intervals" note="300 match resamples · median and P5–P95" className="mb-6" testid="val-bootstrap">
              <ResponsiveContainer width="100%" height={380}>
                <ScatterChart margin={{ left: 10 }}>
                  <CartesianGrid stroke="#1A2234" /><XAxis type="number" dataKey="boot_median_rank" name="Rank" {...AX} domain={[0, "auto"]} />
                  <YAxis type="number" dataKey="y" {...AX} reversed domain={[0, 16]} ticks={top.map((t) => t.y)} tickFormatter={(v) => top[v - 1]?.name || ""} tick={{ fontSize: 11, fill: "#C9CEDA" }} width={170} interval={0} />
                  <Tooltip {...TT} content={({ payload }) => payload?.[0] ? <div className="panel p-2 text-xs"><b>{payload[0].payload.name}</b><br />median {fmt(payload[0].payload.boot_median_rank, 0)} · P5–P95 {fmt(payload[0].payload.boot_rank_p05, 0)}–{fmt(payload[0].payload.boot_rank_p95, 0)} · top-10 {fmt(payload[0].payload.boot_top10_pct, 0)}%</div> : null} />
                  <Scatter data={top} fill={disc === "batting" ? "#8B5CF6" : "#D4AF37"}><ErrorBar dataKey="err" direction="x" stroke="#8B93A7" width={4} /></Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            </Panel>
            <div className="grid xl:grid-cols-2 gap-6 mb-6">
              <Panel title="Pressure-threshold sensitivity">
                <DataTable testid="val-threshold" search={false} rows={d.threshold_sensitivity} cols={[
                  { key: "q_mod", label: "Moderate from", num: true }, { key: "q_high", label: "High from", num: true }, { key: "n_qualified", label: "Qualified", num: true },
                  { key: "top10_overlap", label: "Top-10 overlap", num: true }, { key: "spearman_common", label: "Spearman", num: true }]} />
              </Panel>
              <Panel title="Minimum-sample sensitivity">
                <DataTable testid="val-sample" search={false} rows={d.sample_sensitivity} cols={[
                  { key: "scale", label: "Scale", num: true }, { key: "n_min", label: "Min pressure balls", num: true }, { key: "n_qualified", label: "Qualified", num: true }, { key: "top10_overlap", label: "Top-10 overlap", num: true }]} />
              </Panel>
            </div>
            <div className="grid xl:grid-cols-2 gap-6 mb-6">
              <Panel title="Scoring-weight sensitivity" note={`${g.length} specifications · mean overlap ${fmt(g.reduce((a, x) => a + x.top10_overlap, 0) / g.length)}`}>
                <DataTable testid="val-weights" search={false} pageSize={15} rows={g} cols={[
                  { key: "w_quality", label: "w Q", num: true }, { key: "w_delta", label: "w D", num: true }, { key: "w_consistency", label: "w C", num: true },
                  { key: "spearman_vs_base", label: "Spearman", num: true }, { key: "top10_overlap", label: "Top-10 overlap", num: true }]} />
              </Panel>
              <Panel title="Model comparison · component correlation" note="double-counting check">
                <DataTable testid="val-corr" search={false} rows={Object.entries(d.component_corr).map(([k, v]) => ({ k, ...v }))} cols={[
                  { key: "k", label: "" }, { key: "quality", label: "Q", num: true }, { key: "delta", label: "D", num: true }, { key: "consistency", label: "C", num: true }]} />
                <p className="text-xs text-[var(--muted)] mt-3">Q and C are correlated (both reward positive pressure value), so C is capped at 25% weight; D is largely independent and captures rise-vs-baseline.</p>
              </Panel>
            </div>
            <Panel title="Stability & outlier influence per player">
              <DataTable testid="val-players" rows={d.ranking.slice(0, 30)} csvName={`${disc}_stability.csv`} cols={[
                { key: "rank", label: "#", num: true }, { key: "name", label: "Player" }, { key: "rating", label: "Rating", num: true, render: (r) => fmt(r.rating) },
                { key: "boot_median_rank", label: "Boot median", num: true, render: (r) => fmt(r.boot_median_rank, 0) },
                { key: "boot_top10_pct", label: "Boot top-10 %", num: true, render: (r) => fmt(r.boot_top10_pct, 0) },
                { key: "weight_top10_pct", label: "Weights top-10 %", num: true, render: (r) => fmt(r.weight_top10_pct, 0) },
                { key: "rating_wo_best", label: "Rating w/o best inns", num: true, render: (r) => fmt(r.rating_wo_best) },
                { key: "reliability", label: "Reliability", num: true, render: (r) => fmt(r.reliability, 2) },
                { key: "ci", label: "Raw RV/100 90% CI", num: true, render: (r) => `${fmt(r.ci_low)} … ${fmt(r.ci_high)}` },
                { key: "press_balls", label: "Sample", num: true, render: (r) => int(r.press_balls) },
              ]} />
            </Panel>
          </>
        );
      }}
    </Loading>
  );
}
