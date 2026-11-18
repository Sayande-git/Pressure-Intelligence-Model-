import { useRef, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileText, Upload } from "lucide-react";
import { Badge, Btn, DataTable, Loading, PageHeader, Panel, Stat } from "../components/kit";
import { API, exportUrl, useData } from "../lib/api";

const FILES = [
  ["methodology_report.pdf", "Professional PDF methodology report (25 sections, charts, player proof)"],
  ["batting_rankings.csv", "All qualified batters with components, stability and evidence fields"],
  ["bowling_rankings.csv", "All qualified bowlers with components, stability and evidence fields"],
  ["player_eligibility.csv", "Player universe, identity sources, cap flags, coverage"],
  ["venues.csv", "Venue scoring, chase, pace/spin outcomes, factors"],
  ["engineered_deliveries.csv.gz", "Every modelled delivery: state, WP, LI, tier, expectation, RV (reproducibility)"],
];

const Versions = () => {
  const qc = useQueryClient();
  const fileRef = useRef();
  const [busy, setBusy] = useState(false);
  const v = useQuery({ queryKey: ["versions"], queryFn: () => axios.get(`${API}/versions`).then((r) => r.data), refetchInterval: (q) => (q.state.data?.job?.state === "running" ? 3000 : false) });
  const upload = async (f) => {
    if (!f) return;
    setBusy(true);
    const fd = new FormData();
    fd.append("file", f);
    try {
      const r = await axios.post(`${API}/dataset/upload`, fd);
      toast.success(`Pipeline started on ${r.data.files.length} files`);
      v.refetch();
    } catch (e) { toast.error(e.response?.data?.detail || "Upload failed"); }
    setBusy(false);
  };
  const activate = async (ver) => { await axios.post(`${API}/versions/${ver}/activate`); qc.invalidateQueries(); toast.success(`Version ${ver} active`); };
  return (
    <Panel title="Dataset versions & re-analysis" note={v.data?.job?.state !== "idle" ? `Job: ${v.data?.job?.state} — ${v.data?.job?.message}` : ""} testid="versions-panel">
      <div className="flex items-center gap-3 mb-4">
        <input ref={fileRef} type="file" accept=".zip" className="hidden" data-testid="dataset-upload-input" onChange={(e) => upload(e.target.files[0])} />
        <Btn icon={Upload} testid="dataset-upload-btn" onClick={() => fileRef.current.click()}>{busy ? "Uploading…" : "Upload new data pack (.zip)"}</Btn>
        <span className="text-xs text-[var(--muted)]">Archives the new files, diffs schemas, re-runs audit → pressure → ratings → validation → report. Old rankings are never carried over.</span>
      </div>
      {v.data && <DataTable testid="versions-table" search={false} rows={v.data.versions} cols={[
        { key: "version", label: "Version", render: (r) => <span className="num text-[var(--gold)]">{r.version}</span> }, { key: "generated_at", label: "Generated", render: (r) => r.generated_at?.slice(0, 19) },
        { key: "files", label: "Files", render: (r) => r.files.length }, { key: "changes", label: "Schema changes vs previous", render: (r) => <span className="text-xs">{Object.keys(r.schema_changes_vs_previous || {}).length ? JSON.stringify(r.schema_changes_vs_previous) : "none"}</span> },
        { key: "top", label: "Top batter / bowler", render: (r) => <span className="text-xs">{r.top_bat?.[0]} / {r.top_bowl?.[0]}</span> },
        { key: "act", label: "", render: (r) => r.version === v.data.current ? <Badge tone="Verified">Active</Badge> : <Btn testid={`activate-${r.version}`} onClick={() => activate(r.version)}>Activate</Btn> },
      ]} />}
    </Panel>
  );
};

export default function Reports() {
  const q = useData("requirements");
  return (
    <Loading q={q}>
      {(rq) => (
        <>
          <PageHeader kicker="Phase 10 · Reporting" title="Reports & Exports" testid="reports-header">
            <Btn icon={FileText} href={exportUrl("methodology_report.pdf")} testid="download-report-header">Download PDF report</Btn>
          </PageHeader>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6 [&>*]:min-w-0">
            <Panel title="Exports" testid="exports-panel">
              <ul className="divide-y divide-[var(--line)]">
                {FILES.map(([f, d]) => (
                  <li key={f} className="flex items-center gap-4 py-3">
                    <div className="flex-1"><div className="num text-sm text-white">{f}</div><div className="text-xs text-[var(--muted)]">{d}</div></div>
                    <Btn icon={Download} href={exportUrl(f)} testid={`export-${f.split(".")[0]}`}>Download</Btn>
                  </li>
                ))}
              </ul>
            </Panel>
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <Stat testid="req-official" label="Official coverage" value={`${rq.official_completion}%`} accent="gold" />
                {Object.entries(rq.area_completion).map(([k, v]) => <Stat key={k} testid={`req-area-${k.toLowerCase().replace(/\s/g, "-")}`} label={k} value={`${v}%`} />)}
              </div>
              <Versions />
            </div>
          </div>
          <Panel title="Official requirement coverage tracker">
            <DataTable testid="requirements-table" rows={rq.items} csvName="requirement_coverage.csv" pageSize={40} cols={[
              { key: "area", label: "Area" }, { key: "requirement", label: "Requirement", render: (r) => <span className="text-white whitespace-normal">{r.requirement}</span> },
              { key: "official", label: "Type", render: (r) => (r.official ? "Official" : "Enhancement") },
              { key: "status", label: "Status", render: (r) => <Badge>{r.status}</Badge> }, { key: "evidence", label: "Evidence location", render: (r) => <span className="text-xs text-[var(--muted)] whitespace-normal">{r.evidence}</span> },
            ]} />
          </Panel>
        </>
      )}
    </Loading>
  );
}
