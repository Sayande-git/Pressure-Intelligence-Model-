import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from "recharts";
import { Badge, Btn, DataTable, Loading, PageHeader, Panel } from "../components/kit";
import { fmt, int, useData } from "../lib/api";
import { AX, TT } from "./Pressure";

const HomeAway = ({ store, bat }) => (
  <DataTable testid={`venue-homeaway-${bat ? "bat" : "bowl"}`} search={false} rows={store.ranking.slice(0, 10).map((r) => {
    const h = store.rr_home?.[String(r.player_id)] || {};
    const H = h["RR home venues"], O = h["Other venues"];
    return { name: r.name, hb: H?.balls, hm: bat ? H?.sr : H?.econ, hrv: H?.rv100, ob: O?.balls, om: bat ? O?.sr : O?.econ, orv: O?.rv100 };
  })} cols={[
    { key: "name", label: "Player" }, { key: "hb", label: "RR-home balls", num: true, render: (r) => int(r.hb) },
    { key: "hm", label: bat ? "Home SR" : "Home econ", num: true, render: (r) => fmt(r.hm, bat ? 1 : 2) }, { key: "hrv", label: "Home RV/100", num: true, render: (r) => fmt(r.hrv) },
    { key: "ob", label: "Other balls", num: true, render: (r) => int(r.ob) }, { key: "om", label: bat ? "Other SR" : "Other econ", num: true, render: (r) => fmt(r.om, bat ? 1 : 2) },
    { key: "orv", label: "Other RV/100", num: true, render: (r) => fmt(r.orv) },
  ]} />
);

export default function Venues() {
  const q = useData("venues");
  const bat = useData("batting");
  const bowl = useData("bowling");
  const [only, setOnly] = useState("all");
  return (
    <Loading q={q}>
      {(v) => {
        const rows = v.venues.filter((x) => only === "all" || (only === "rr" ? v.rr_home_venue_ids.includes(x.venue_id) : x.competitions.includes(only)));
        const top = [...v.venues].filter((x) => x.avg_first_innings && x.matches >= 8).slice(0, 18);
        return (
          <>
            <PageHeader kicker="Phase 4 · Context Engineering" title="Venue Intelligence" testid="venue-header" />
            <Panel title="What the data can and cannot say" className="mb-6" testid="venue-limits">
              <div className="grid md:grid-cols-3 gap-6 text-sm leading-relaxed">
                <p><b className="text-white">Observed:</b> venue ID, country, scores, chase results, pace/spin outcomes per venue. Venue factor = shrunk ratio of venue runs/ball to its competition mean; Kruskal–Wallis H = <span className="num">{v.meta.kruskal_H}</span>, p = <span className="num">{v.meta.kruskal_p}</span> → adjustment {v.meta.adjustment_applied ? "applied" : "not applied"}.</p>
                <p><b className="text-white">Inferred (labelled):</b> IPL home team per venue from fixture patterns. RR inferred home venue IDs: <span className="num text-[var(--gold)]">{v.rr_home_venue_ids.join(", ")}</span> (consistent with Jaipur and Guwahati, but venue names are not in the data).</p>
                <p><b className="text-white">Not available:</b> stadium names, boundary dimensions, pitch reports, dew, weather, humidity. None are invented. Spin/pace "assistance" is shown only as observed economy and wicket share.</p>
              </div>
            </Panel>
            <Panel title="Average first-innings score by venue" note="venues with ≥8 matches" className="mb-6" testid="venue-chart">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={top.map((x) => ({ ...x, label: `#${x.venue_id}` }))}><CartesianGrid stroke="#1A2234" vertical={false} /><XAxis dataKey="label" {...AX} /><YAxis {...AX} /><Tooltip {...TT} /><Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="avg_first_innings" name="Avg 1st inns" fill="#8B5CF6" /><Bar dataKey="avg_second_innings" name="Avg 2nd inns" fill="#3A4560" /></BarChart>
              </ResponsiveContainer>
            </Panel>
            <Panel title="Venue comparison" className="mb-6">
              <DataTable testid="venue-table" rows={rows} csvName="venues.csv" filters={
                <div className="flex gap-1">{[["all", "All"], ["rr", "RR home"], ["IPL", "IPL"], ["T20I", "T20I"]].map(([k, l]) => <Btn key={k} testid={`venue-filter-${k}`} active={only === k} onClick={() => setOnly(k)}>{l}</Btn>)}</div>}
                cols={[
                  { key: "venue_id", label: "Venue ID", num: true, render: (r) => <span className="flex items-center gap-2 justify-end">{v.rr_home_venue_ids.includes(r.venue_id) && <Badge tone="Robust">RR</Badge>}{r.venue_id}</span> },
                  { key: "country", label: "Country" }, { key: "competitions", label: "Comps" }, { key: "ipl_home_team_inferred", label: "IPL home (inferred)" },
                  { key: "matches", label: "M", num: true }, { key: "avg_first_innings", label: "Avg 1st", num: true }, { key: "avg_second_innings", label: "Avg 2nd", num: true },
                  { key: "run_rate", label: "RPO", num: true }, { key: "wkts_per_match", label: "Wkts/M", num: true }, { key: "chasing_win_pct", label: "Chase win %", num: true },
                  { key: "boundary_pct", label: "Bdry %", num: true }, { key: "pace_econ", label: "Pace econ", num: true }, { key: "spin_econ", label: "Spin econ", num: true },
                  { key: "spin_wkt_share", label: "Spin wkt %", num: true }, { key: "venue_factor", label: "Factor", num: true },
                ]} />
            </Panel>
            <div className="grid xl:grid-cols-2 gap-6">
              <Panel title="Top-10 batters · RR home vs elsewhere">{bat.data && <HomeAway store={bat.data} bat />}</Panel>
              <Panel title="Top-10 bowlers · RR home vs elsewhere">{bowl.data && <HomeAway store={bowl.data} bat={false} />}</Panel>
            </div>
          </>
        );
      }}
    </Loading>
  );
}
