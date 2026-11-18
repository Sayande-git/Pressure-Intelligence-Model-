import { DataTable, KV, Loading, PageHeader, Panel } from "../components/kit";
import { int, useData } from "../lib/api";

export default function DataIntel() {
  const q = useData("audit");
  return (
    <Loading q={q}>
      {(a) => (
        <>
          <PageHeader kicker="Phase 1 · Data Audit" title="Data Intelligence" testid="data-header" />
          <Panel title="Tables in the data pack" className="mb-6">
            <DataTable testid="audit-tables" search={false} rows={a.tables} csvName="audit_tables.csv" cols={[
              { key: "table", label: "Table" }, { key: "rows", label: "Rows", num: true, render: (r) => int(r.rows) },
              { key: "columns", label: "Columns", num: true }, { key: "duplicate_rows", label: "Duplicate rows", num: true },
              { key: "missing_cells", label: "Missing cells", num: true, render: (r) => int(r.missing_cells) },
              { key: "mbc", label: "Missing by column", text: (r) => JSON.stringify(r.missing_by_column), render: (r) => <span className="text-xs text-[var(--muted)] whitespace-normal">{Object.entries(r.missing_by_column).map(([k, v]) => `${k}: ${v}`).join(" · ") || "none"}</span> },
            ]} />
          </Panel>
          <div className="grid lg:grid-cols-3 gap-6 mb-6">
            <Panel title="Integrity checks" testid="audit-integrity">
              <KV rows={[
                ["Delivery key duplicates", a.delivery_key_duplicates], ["Matches", a.matches_total], ["…with deliveries", a.matches_with_deliveries],
                ["…without deliveries", a.matches_without_deliveries], ["Orphan delivery matches", a.deliveries_without_match],
                ["Abandoned / no result", a.abandoned_or_no_result], ["Rain-revised targets", a.rain_revised_matches],
                ["Super-over deliveries (excluded)", a.super_over_deliveries], ["IDs with >1 name", a.ids_with_multiple_names],
                ["Impact-player rows", a.impact_player_rows],
              ]} />
            </Panel>
            <Panel title="Team-total reconstruction" note="vs official run margins" testid="audit-reconciliation">
              <KV rows={[["Matches checked", a.reconciliation.matches_checked], ["Exact", `${a.reconciliation.exact_pct}%`], ["Within ±3 runs", `${a.reconciliation.within3_pct}%`], ["Median abs error", a.reconciliation.median_abs_error]]} />
              <p className="text-xs text-[var(--muted)] mt-4 leading-relaxed">{a.extras_encoding_note}</p>
            </Panel>
            <Panel title="Competition scope" testid="audit-scope">
              <KV rows={[...Object.entries(a.competitions_by_format).map(([k, v]) => [`${k} competitions`, v]), ...Object.entries(a.seasons).map(([k, v]) => [`Season ${k}`, v])]} />
              <p className="text-xs text-[var(--muted)] mt-4">Non-T20I: {a.non_t20i_competitions.join(", ")}</p>
              <p className="text-xs text-amber-300 mt-2">Domestic (SMAT/VHT/Ranji) competitions found: {a.domestic_competitions_found.length ? a.domestic_competitions_found.join(", ") : "none"}</p>
            </Panel>
          </div>
          <div className="grid lg:grid-cols-3 gap-6">
            <Panel title="Extras" testid="audit-extras"><KV rows={Object.entries(a.extras_breakdown)} /></Panel>
            <Panel title="Dismissals" testid="audit-dismissals"><KV rows={Object.entries(a.dismissal_breakdown)} /></Panel>
            <Panel title="Legal balls per over" note="after excluding wide / no-ball / other" testid="audit-overs"><KV rows={Object.entries(a.legal_balls_per_over)} /></Panel>
          </div>
          <Panel title="Context data availability" className="mt-6" testid="audit-context">
            <p className="text-sm">Venue names in data: <b>{String(a.venue_name_available)}</b> · Unique venue IDs: <b className="num">{a.unique_venue_ids}</b> · Pitch / weather / boundary fields: <b>{a.pitch_weather_boundary_fields.length ? a.pitch_weather_boundary_fields.join(", ") : "none"}</b>.
              Homonym player names (resolved by ID): {a.homonym_player_names.join(", ")}.</p>
          </Panel>
        </>
      )}
    </Loading>
  );
}
