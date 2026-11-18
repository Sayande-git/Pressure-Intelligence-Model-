import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, DataTable, KV, Panel } from "./kit";
import { fmt, int } from "../lib/api";
import { AX, TT } from "../pages/Pressure";

const tierCols = (bat) => bat
  ? [["runs", "Runs"], ["balls", "Balls"], ["outs", "Outs"], ["sr", "SR"], ["avg", "Avg"], ["bdry_pct", "Bdry %"], ["dot_pct", "Dot %"], ["rv100", "RV/100"]]
  : [["runs", "Runs"], ["balls", "Legal balls"], ["wkts", "Wkts"], ["econ", "Econ"], ["avg", "Avg"], ["sr", "SR"], ["dot_pct", "Dot %"], ["bdry_pct", "Bdry %"], ["rv100", "RV/100"]];

const Split = ({ obj, bat, testid, label = "Split" }) => {
  const rows = Object.entries(obj || {}).map(([k, v]) => ({ k, ...v }));
  return (
    <DataTable testid={testid} search={false} pageSize={50} rows={rows} cols={[
      { key: "k", label, render: (r) => r.k.includes("|") ? <span>{r.k.split("|")[0]} <Badge tone={r.k.split("|")[1] === "Pressure" ? "High" : "Normal"}>{r.k.split("|")[1]}</Badge></span> : <Badge>{r.k}</Badge> },
      ...tierCols(bat).map(([k, l]) => ({ key: k, label: l, num: true, render: (r) => (["runs", "balls", "outs", "wkts"].includes(k) ? int(r[k]) : fmt(r[k], k === "econ" ? 2 : 1)) })),
    ]} />
  );
};

export const MatchEvidence = ({ rows, bat, testid }) => (
  <DataTable testid={testid} search={false} rows={rows} cols={[
    { key: "match_id", label: "Match ID", num: true }, { key: "date", label: "Date" }, { key: "comp", label: "Competition" }, { key: "innings", label: "Inn", num: true },
    { key: "opp", label: "Opponent" },
    bat ? { key: "rb", label: "R (B)", num: true, render: (r) => `${int(r.runs)} (${int(r.balls)})${r.outs ? "" : "*"}` } : { key: "fig", label: "Balls-R-W", num: true, render: (r) => `${int(r.balls)}-${int(r.runs)}-${int(r.wkts)}` },
    { key: "press_balls", label: "Pressure balls", num: true }, { key: "press_runs", label: bat ? "Pressure runs" : "Pressure conceded", num: true },
    { key: "rv", label: "Innings RV", num: true, render: (r) => <span className={r.rv >= 0 ? "text-emerald-300" : "text-red-300"}>{fmt(r.rv)}</span> },
    { key: "max_li", label: "Peak LI", num: true, render: (r) => fmt(r.max_li, 2) },
    { key: "state", label: "State at entry", render: (r) => `${int(r.entry_score)}/${r.entry_wk}${r.target ? ` · target ${int(r.target)}, ${int(r.entry_bl)} balls left` : ""}` },
    { key: "result", label: "Result", render: (r) => <span className="text-xs text-[var(--muted)]">{r.result}</span> },
  ]} />
);

export default function PlayerProfile({ r, profile, disc, meta }) {
  const bat = disc === "batting";
  const tiers = profile?.tiers || {};
  const chart = Object.entries(tiers).map(([t, v]) => ({ tier: t, rv100: v.rv100, [bat ? "sr" : "econ"]: bat ? v.sr : v.econ }));
  return (
    <div className="space-y-6" data-testid="player-profile">
      <div className="grid lg:grid-cols-3 gap-6">
        <Panel title={r.name} note={`${r.role} · ID ${r.player_id}`} testid="profile-summary">
          <KV rows={[
            ["Rating", fmt(r.rating, 2)], ["Rank", r.rank], ["Q · pressure quality", fmt(r.quality, 2)], ["Baseline (normal)", fmt(r.baseline, 2)],
            ["D · rise vs baseline", fmt(r.delta, 2)], ["C · consistency", `${fmt(r.consistency, 3)} (${int(r.p_succ)}/${int(r.p_inn)})`],
            ["Reliability n/(n+k)", fmt(r.reliability, 2)], ["Pressure sample", `${int(r.press_balls)} ${bat ? "balls" : "deliveries"}`],
            ["Raw RV/100 · 90% CI", `${fmt(r.press_rv100_raw)} [${fmt(r.ci_low)}, ${fmt(r.ci_high)}]`], ["Matches", r.matches],
            ["Bootstrap rank P5–P95", `${fmt(r.boot_rank_p05, 0)}–${fmt(r.boot_rank_p95, 0)}`], ["Uncapped lens", r.capped_in_data ? "Capped (T20I)" : "Unverified"],
          ]} />
          <div className="text-xs text-[var(--muted)] mt-3">{(r.teams || []).join(", ")}</div>
        </Panel>
        <Panel title="Rating calculation" className="lg:col-span-2" testid="profile-calc">
          <pre className="num text-[12px] text-[var(--gold)] bg-[var(--bg)] border border-[var(--line)] rounded-sm p-3 whitespace-pre-wrap">{`Q = ΣRV_pressure / (n + k) × 100 = ${fmt(r.quality, 2)}     (n = ${int(r.press_balls)}, k = ${meta.k_pressure})
Baseline = ΣRV_normal / (n_normal + k_n) × 100 = ${fmt(r.baseline, 2)}     (n_normal = ${int(r.normal_balls)})
D = Q − Baseline = ${fmt(r.delta, 2)}
C = (${int(r.p_succ)} + 10 × ${meta.league_innings_success}) / (${int(r.p_inn)} + 10) = ${fmt(r.consistency, 3)}
Rating = 50 + 10 × (0.50·z(Q) + 0.25·z(D) + 0.25·z(C)) = ${fmt(r.rating, 2)}
Without best pressure innings → ${fmt(r.rating_wo_best, 2)}`}</pre>
          {profile?.next_ranked && <p className="text-xs text-[var(--muted)] mt-3">Next ranked: <b className="text-white">{profile.next_ranked.name}</b> — rating {profile.next_ranked.rating}, Q {profile.next_ranked.quality}, D {profile.next_ranked.delta}, C {profile.next_ranked.consistency}</p>}
          <ResponsiveContainer width="100%" height={170}>
            <BarChart data={chart}><CartesianGrid stroke="#1A2234" vertical={false} /><XAxis dataKey="tier" {...AX} /><YAxis {...AX} /><Tooltip {...TT} /><Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="rv100" name="RV per 100 (vs context)" fill={bat ? "#8B5CF6" : "#D4AF37"} /><Bar dataKey={bat ? "sr" : "econ"} name={bat ? "Strike rate" : "Economy"} fill="#3A4560" /></BarChart>
          </ResponsiveContainer>
        </Panel>
      </div>
      <Panel title="Normal · moderate · high pressure"><Split testid="profile-tiers" obj={tiers} bat={bat} label="Tier" /></Panel>
      <div className="grid xl:grid-cols-2 gap-6">
        <Panel title="Phase-wise"><Split testid="profile-phases" obj={profile?.phases} bat={bat} label="Phase" /></Panel>
        <Panel title="Competition-wise"><Split testid="profile-comps" obj={profile?.competitions} bat={bat} label="Competition" /></Panel>
      </div>
      <Panel title="Venue-wise (most-played venue IDs)"><Split testid="profile-venues" obj={profile?.venues} bat={bat} label="Venue ID" /></Panel>
      <Panel title="Match-level evidence" note={`best 6 and worst 2 of ${profile?.pressure_innings} pressure innings (≥6 pressure balls)`}>
        <MatchEvidence rows={profile?.matches || []} bat={bat} testid="profile-matches" />
      </Panel>
    </div>
  );
}
