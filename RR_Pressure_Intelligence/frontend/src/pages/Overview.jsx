import { Link } from "react-router-dom";
import { Badge, Loading, PageHeader, Panel, Stat } from "../components/kit";
import { fmt, int, useData } from "../lib/api";

const TopList = ({ rows, disc }) => (
  <ol className="divide-y divide-[var(--line)]" data-testid={`overview-top-${disc}`}>
    {rows.slice(0, 10).map((r, i) => (
      <li key={r.player_id} className="flex items-center gap-4 py-2.5">
        <span className="num w-6 text-[var(--muted)]">{String(i + 1).padStart(2, "0")}</span>
        <div className="flex-1 min-w-0">
          <div className="text-white truncate">{r.name}</div>
          <div className="text-[11px] text-[var(--muted)]">{r.role} · {int(r.press_balls)} pressure {disc === "bat" ? "balls" : "deliveries"}</div>
        </div>
        {r.robust && <Badge tone="Robust">Robust</Badge>}
        <span className={`num text-lg ${disc === "bat" ? "text-[var(--purple)]" : "text-[var(--gold)]"}`}>{fmt(r.rating)}</span>
      </li>
    ))}
  </ol>
);

export default function Overview() {
  const q = useData("overview");
  const p = useData("pressure");
  return (
    <Loading q={q}>
      {(o) => (
        <>
          <PageHeader kicker="Executive Overview · War Room" title="Who delivers when it matters" testid="overview-header" />
          <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-3 mb-6">
            <Stat testid="stat-version" label="Dataset" value={o.version} accent="gold" sub={o.generated_at.slice(0, 10)} />
            <Stat testid="stat-players" label="Players" value={int(o.players.total_players)} />
            <Stat testid="stat-eligible" label="Eligible (PDF scope)" value={int(o.players.official_eligible)} />
            <Stat testid="stat-capped" label="Capped in data" value={int(o.players.capped_in_data_ineligible_lens)} sub="Uncapped lens: ineligible" />
            <Stat testid="stat-unverified" label="Unverified" value={int(o.players.unverified_lens)} sub="No cap in data" />
            <Stat testid="stat-matches" label="Matches" value={int(o.matches)} sub={`${o.matches_with_deliveries} with deliveries`} />
            <Stat testid="stat-deliveries" label="Deliveries" value={int(o.deliveries)} />
            <Stat testid="stat-requirements" label="Official reqs" value={`${o.requirements}%`} accent="purple" sub={`Data quality ${o.data_quality}%`} />
          </div>
          <div className="grid lg:grid-cols-2 gap-6 mb-6">
            <Panel title="Top 10 Batters Under Pressure" note={<Link to="/rankings" className="text-[var(--purple)]" data-testid="overview-link-rankings">Full rankings →</Link>}>
              <TopList rows={o.top_bat} disc="bat" />
            </Panel>
            <Panel title="Top 10 Bowlers Under Pressure" note={<Link to="/evidence" className="text-[var(--gold)]" data-testid="overview-link-evidence">Evidence →</Link>}>
              <TopList rows={o.top_bowl} disc="bowl" />
            </Panel>
          </div>
          <Panel title="Key analytical findings" testid="overview-findings">
            <ul className="grid md:grid-cols-2 gap-x-10 gap-y-3 text-sm text-[var(--text)]">
              <li>Pressure = win-probability leverage per delivery (pre-ball state only). Chasing WP model out-of-sample AUC <span className="num text-[var(--gold)]">{p.data?.wp_validation.innings_2.auc ?? "…"}</span>.</li>
              <li>League strike rate falls from <span className="num">{p.data?.tiers[0].strike_rate}</span> (normal) to <span className="num">{p.data?.tiers[2].strike_rate}</span> under high pressure; dot-ball share rises.</li>
              <li>Shrinkage strength k = <span className="num">{o.bat_meta.k_pressure}</span> (bat) / <span className="num">{o.bowl_meta.k_pressure}</span> (bowl) balls: pressure skill is real but noisy, so small samples are heavily discounted.</li>
              <li>Qualification: ≥<span className="num">{o.bat_meta.n_min_pressure_balls}</span> pressure balls faced ({o.bat_meta.n_qualified} batters) and ≥<span className="num">{o.bowl_meta.n_min_pressure_balls}</span> pressure deliveries ({o.bowl_meta.n_qualified} bowlers).</li>
              <li>Venue scoring differs significantly (Kruskal–Wallis p = <span className="num">{o.venue_meta.kruskal_p}</span>) → venue-adjusted expectations applied.</li>
              <li>No SMAT / Vijay Hazare / Ranji data in the pack; uncapped status can only be disproven (T20I caps), not proven. See Eligibility.</li>
            </ul>
          </Panel>
        </>
      )}
    </Loading>
  );
}
