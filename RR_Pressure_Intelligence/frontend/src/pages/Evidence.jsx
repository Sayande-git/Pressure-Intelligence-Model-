import { useState } from "react";
import { Btn, Loading, PageHeader, Panel } from "../components/kit";
import PlayerProfile from "../components/PlayerProfile";
import { useData } from "../lib/api";

const STEPS = ["Raw ball_by_ball.csv rows", "Pre-ball match state (score, wickets, balls left, target)", "Win probability → Leverage Index → pressure tier",
  "Context expectation E[runs], P[wicket] per cell + venue factor", "Runs value per ball (RV)", "Shrunk Q, D, C components", "Rating → rank"];

export default function Evidence() {
  const [disc, setDisc] = useState("batting");
  const q = useData(disc);
  const [pid, setPid] = useState(null);
  return (
    <Loading q={q}>
      {(d) => {
        const top = d.ranking.slice(0, 10);
        const cur = top.find((r) => r.player_id === pid) || top[0];
        return (
          <>
            <PageHeader kicker="Evidence-first proof system" title="Evidence Centre" testid="evidence-header">
              <Btn testid="evidence-bat" active={disc === "batting"} onClick={() => { setDisc("batting"); setPid(null); }}>Batters</Btn>
              <Btn testid="evidence-bowl" active={disc === "bowling"} onClick={() => { setDisc("bowling"); setPid(null); }}>Bowlers</Btn>
            </PageHeader>
            <Panel title="Evidence trail" className="mb-6" testid="evidence-trail">
              <ol className="flex flex-wrap gap-2 text-xs">
                {STEPS.map((s, i) => <li key={s} className="border border-[var(--line)] rounded-sm px-3 py-2"><span className="num text-[var(--gold)] mr-2">{i + 1}</span>{s}</li>)}
              </ol>
              <p className="text-xs text-[var(--muted)] mt-3">Every delivery with its engineered state, LI, tier, expectation and RV is downloadable (Reports → engineered_deliveries.csv.gz), so any figure below can be recomputed independently.</p>
            </Panel>
            <div className="flex flex-wrap gap-2 mb-6" data-testid="evidence-player-picker">
              {top.map((r, i) => <Btn key={r.player_id} testid={`evidence-player-${i + 1}`} active={cur.player_id === r.player_id} onClick={() => setPid(r.player_id)}>{i + 1}. {r.name}</Btn>)}
            </div>
            <PlayerProfile r={cur} profile={d.profiles[String(cur.player_id)]} disc={disc} meta={d.meta} />
          </>
        );
      }}
    </Loading>
  );
}
