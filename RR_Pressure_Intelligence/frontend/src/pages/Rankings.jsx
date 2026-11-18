import { useState } from "react";
import { Btn, DataTable, Loading, PageHeader, Panel } from "../components/kit";
import { uncappedLensStatus, useData, useOverrides } from "../lib/api";
import { rankCols } from "./Discipline";

export default function Rankings() {
  const bat = useData("batting");
  const bowl = useData("bowling");
  const ov = useOverrides();
  const [lens, setLens] = useState("official");
  const pick = (rows) => (lens === "official" ? rows : rows.filter((r) => uncappedLensStatus(r, ov.data) !== "Ineligible").slice()).slice(0, 10).map((r, i) => ({ ...r, rank: i + 1 }));
  return (
    <Loading q={bat}>
      {(b) => (
        <>
          <PageHeader kicker="Phase 8 · Ranking Engine" title="Player Rankings" testid="rankings-header">
            <Btn testid="lens-official" active={lens === "official"} onClick={() => setLens("official")}>Official submission</Btn>
            <Btn testid="lens-uncapped" active={lens === "uncapped"} onClick={() => setLens("uncapped")}>Uncapped lens</Btn>
          </PageHeader>
          <p className="text-sm text-[var(--muted)] mb-6 max-w-4xl" data-testid="rankings-lens-note">
            {lens === "official"
              ? "Official submission: all IPL + T20I players in the data pack (Round-1 PDF scope). These are the exact lists to enter in the Unstop dropdowns and match the PDF report."
              : "Uncapped lens: removes players proven capped (T20I appearance in data) or manually marked Ineligible. Remaining names are Unverified unless marked Eligible on the Eligibility page. Ratings are unchanged; only the pool is filtered."}
          </p>
          <Panel title="Top 10 batters under pressure" note={lens === "uncapped" ? `${pick(b.ranking).length} qualify in this lens` : ""} className="mb-6">
            <DataTable testid="rank-bat-table" search={false} rows={pick(b.ranking)} cols={rankCols(true)} csvName={`top10_batters_${lens}.csv`} />
          </Panel>
          <Panel title="Top 10 bowlers under pressure" note={lens === "uncapped" && bowl.data ? `${pick(bowl.data.ranking).length} qualify in this lens${pick(bowl.data.ranking).length < 10 ? " — fewer than 10 meet the sample rule; list is not padded" : ""}` : ""}>
            {bowl.data && <DataTable testid="rank-bowl-table" search={false} rows={pick(bowl.data.ranking)} cols={rankCols(false)} csvName={`top10_bowlers_${lens}.csv`} />}
          </Panel>
          <p className="text-xs text-[var(--muted)] mt-4">Q = shrunk pressure runs-value per 100 vs context · D = Q minus own normal baseline · C = shrunk share of pressure innings with positive value · Robust = top-10 in ≥50% of bootstrap resamples and ≥60% of weight specifications.</p>
        </>
      )}
    </Loading>
  );
}
