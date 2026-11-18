import { useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { Badge, Btn, DataTable, Loading, PageHeader, Panel, Stat } from "../components/kit";
import { API, int, uncappedLensStatus, useData, useOverrides } from "../lib/api";

const OverrideCell = ({ p, overrides }) => {
  const qc = useQueryClient();
  const status = uncappedLensStatus(p, overrides);
  const set = async (s) => {
    try {
      await axios.post(`${API}/eligibility/overrides`, { player_id: p.player_id, status: s, note: "manual review" });
      qc.invalidateQueries({ queryKey: ["overrides"] });
      toast.success(`${p.player_name} marked ${s}`);
    } catch (e) { toast.error("Could not save eligibility decision"); }
  };
  return (
    <select data-testid={`override-${p.player_id}`} value={status} onClick={(e) => e.stopPropagation()} onChange={(e) => set(e.target.value)}
      className="bg-[var(--bg)] border border-[var(--line)] rounded-sm text-xs px-1 py-0.5">
      {["Eligible", "Unverified", "Ineligible"].map((s) => <option key={s}>{s}</option>)}
    </select>
  );
};

export default function Eligibility() {
  const q = useData("eligibility");
  const ov = useOverrides();
  const [f, setF] = useState("all");
  return (
    <Loading q={q}>
      {(e) => {
        const s = e.summary;
        const rows = e.players.filter((p) => {
          const st = uncappedLensStatus(p, ov.data);
          return f === "all" || (f === "bat" ? p.bat_sample : f === "bowl" ? p.bowl_sample : st === f);
        });
        return (
          <>
            <PageHeader kicker="Phase 2 · Player Identification" title="Domestic Player Eligibility" testid="eligibility-header" />
            <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-3 mb-6">
              <Stat testid="elig-total" label="Unique players" value={int(s.total_players)} />
              <Stat testid="elig-official" label="Eligible · PDF scope" value={int(s.official_eligible)} accent="purple" />
              <Stat testid="elig-capped" label="Ineligible · capped" value={int(s.capped_in_data_ineligible_lens)} />
              <Stat testid="elig-unverified" label="Unverified" value={int(s.unverified_lens)} />
              <Stat testid="elig-bat" label="Batting sample OK" value={s.bat_sufficient} />
              <Stat testid="elig-bowl" label="Bowling sample OK" value={s.bowl_sufficient} />
              <Stat testid="elig-domestic" label="Missing domestic stats" value={int(s.missing_domestic)} accent="gold" />
            </div>
            <Panel title="Eligibility logic" className="mb-6" testid="elig-logic">
              <div className="grid md:grid-cols-2 gap-6 text-sm leading-relaxed">
                <p><b className="text-white">Official scope (PDF):</b> the Round-1 brief supplies IPL + T20I data and states no uncapped restriction, so every player in the data pack is eligible for the submitted Top-10s. This is the scope used for the official rankings.</p>
                <p><b className="text-white">Uncapped lens (live Unstop card mentions domestic leagues):</b> a T20I appearance in the data proves a cap → <Badge>Ineligible</Badge>. Absence of a T20I in 2022-26 does not prove uncapped status (Tests/ODIs/pre-2022 not in data) → <Badge>Unverified</Badge>. You can record verified decisions per player below; they persist and feed the Rankings uncapped view.</p>
              </div>
            </Panel>
            <Panel title="Player database">
              <DataTable testid="elig-table" rows={rows} csvName="player_eligibility.csv" initialSort={{ key: "balls_faced", dir: "desc" }}
                filters={<select data-testid="elig-filter" value={f} onChange={(x) => setF(x.target.value)} className="bg-[var(--bg)] border border-[var(--line)] rounded-sm text-xs px-2 py-1.5">
                  <option value="all">All players</option><option value="Ineligible">Uncapped lens: Ineligible</option><option value="Unverified">Uncapped lens: Unverified</option>
                  <option value="Eligible">Uncapped lens: Eligible (manual)</option><option value="bat">Sufficient batting sample</option><option value="bowl">Sufficient bowling sample</option>
                </select>}
                cols={[
                  { key: "player_name", label: "Player" }, { key: "player_id", label: "ID", num: true },
                  { key: "teams", label: "Teams", text: (r) => r.teams.join(", "), render: (r) => <span className="text-xs text-[var(--muted)]">{r.teams.slice(0, 3).join(", ")}</span> },
                  { key: "domestic_status", label: "Domestic status", render: (r) => <span className="text-xs">{r.domestic_status}</span> },
                  { key: "uncapped_status", label: "Uncapped status", render: (r) => <span className="text-xs">{r.uncapped_status}</span> },
                  { key: "eligibility_official", label: "Official", render: () => <Badge>Eligible</Badge> },
                  { key: "lens", label: "Uncapped lens", text: (r) => uncappedLensStatus(r, ov.data), render: (r) => <OverrideCell p={r} overrides={ov.data} /> },
                  { key: "ipl_matches", label: "IPL", num: true }, { key: "t20i_matches", label: "T20I", num: true }, { key: "emerging_matches", label: "Emerging", num: true },
                  { key: "balls_faced", label: "Balls faced", num: true }, { key: "balls_bowled", label: "Balls bowled", num: true },
                  { key: "coverage", label: "Data coverage", text: (r) => `${r.bat_sample ? "bat" : ""} ${r.bowl_sample ? "bowl" : ""}`, render: (r) => <span className="text-xs">{[r.bat_sample && "Bat ✓", r.bowl_sample && "Bowl ✓"].filter(Boolean).join(" · ") || <span className="text-[var(--muted)]">Insufficient</span>} · <span className="text-amber-300/80">domestic missing</span></span> },
                  { key: "in_sources", label: "Identity sources", render: (r) => <span className="text-xs text-[var(--muted)]">{r.in_sources}</span> },
                ]} />
            </Panel>
          </>
        );
      }}
    </Loading>
  );
}
