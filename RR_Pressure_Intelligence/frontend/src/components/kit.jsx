import { Fragment, useEffect, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Download, Search } from "lucide-react";
import { downloadCSV } from "../lib/api";

export const PageHeader = ({ kicker, title, children, testid }) => (
  <div className="flex flex-wrap items-end justify-between gap-4 mb-8 fade-in" data-testid={testid}>
    <div>
      <div className="text-[11px] uppercase tracking-[0.2em] text-[var(--gold)] mb-2">{kicker}</div>
      <h1 className="font-display text-4xl sm:text-5xl font-semibold text-white">{title}</h1>
    </div>
    <div className="flex gap-2 flex-wrap">{children}</div>
  </div>
);

export const Panel = ({ title, note, children, className = "", testid }) => (
  <section className={`panel p-5 fade-in ${className}`} data-testid={testid}>
    {title && (
      <div className="flex items-baseline justify-between mb-4 gap-3">
        <h2 className="font-display text-lg md:text-xl font-semibold uppercase tracking-wide text-white">{title}</h2>
        {note && <span className="text-xs text-[var(--muted)]">{note}</span>}
      </div>
    )}
    {children}
  </section>
);

export const Stat = ({ label, value, sub, accent, testid }) => (
  <div className="panel p-4" data-testid={testid}>
    <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">{label}</div>
    <div className={`num text-2xl mt-2 ${accent === "gold" ? "text-[var(--gold)]" : accent === "purple" ? "text-[var(--purple)]" : "text-white"}`}>{value}</div>
    {sub && <div className="text-xs text-[var(--muted)] mt-1">{sub}</div>}
  </div>
);

const TONES = {
  Eligible: "border-emerald-500/40 text-emerald-300", Ineligible: "border-red-500/40 text-red-300", Unverified: "border-amber-500/40 text-amber-300",
  Verified: "border-emerald-500/40 text-emerald-300", Tested: "border-sky-500/40 text-sky-300", "Not started": "border-slate-500/40 text-slate-400",
  "In progress": "border-amber-500/40 text-amber-300", Implemented: "border-violet-500/40 text-violet-300",
  High: "border-red-500/40 text-red-300", Moderate: "border-amber-500/40 text-amber-300", Normal: "border-slate-500/40 text-slate-300",
  Robust: "border-[var(--gold)]/50 text-[var(--gold)]",
};
export const Badge = ({ children, tone, testid }) => (
  <span data-testid={testid} className={`inline-block border rounded-sm px-1.5 py-0.5 text-[10px] uppercase tracking-wider whitespace-nowrap ${TONES[tone || children] || "border-slate-600 text-slate-300"}`}>{children}</span>
);

export const Btn = ({ children, onClick, href, active, testid, icon: Icon }) => {
  const cls = `inline-flex items-center gap-2 px-3 py-1.5 text-xs uppercase tracking-wider border rounded-sm transition-colors duration-150 ${active ? "bg-[var(--purple-deep)] border-[var(--purple)] text-white" : "border-[var(--line)] text-[var(--text)] hover:border-[var(--purple)] hover:text-white"}`;
  const inner = <>{Icon && <Icon size={14} />}{children}</>;
  return href ? <a href={href} className={cls} data-testid={testid} target="_blank" rel="noreferrer">{inner}</a> : <button className={cls} onClick={onClick} data-testid={testid}>{inner}</button>;
};

export function DataTable({ rows, cols, testid, search = true, pageSize = 25, onRow, csvName, initialSort, filters }) {
  const [q, setQ] = useState("");
  const [sort, setSort] = useState(initialSort || null);
  const [page, setPage] = useState(0);
  useEffect(() => setPage(0), [rows]);
  const data = useMemo(() => {
    let r = rows || [];
    if (q) {
      const s = q.toLowerCase();
      r = r.filter((x) => cols.some((c) => String(c.text ? c.text(x) : x[c.key] ?? "").toLowerCase().includes(s)));
    }
    if (sort) {
      const c = cols.find((k) => k.key === sort.key);
      const v = (x) => (c?.sortVal ? c.sortVal(x) : c?.text && x[sort.key] === undefined ? c.text(x) : x[sort.key]);
      r = [...r].sort((a, b) => {
        const A = v(a), B = v(b);
        if (A == null) return 1;
        if (B == null) return -1;
        return (A > B ? 1 : A < B ? -1 : 0) * (sort.dir === "asc" ? 1 : -1);
      });
    }
    return r;
  }, [rows, q, sort, cols]);
  const pages = Math.max(1, Math.ceil(data.length / pageSize));
  const view = data.slice(page * pageSize, page * pageSize + pageSize);
  return (
    <div data-testid={testid}>
      <div className="flex flex-wrap items-center gap-2 mb-3">
        {search && (
          <label className="flex items-center gap-2 border border-[var(--line)] rounded-sm px-2 py-1.5 bg-[var(--bg)] min-w-[220px]">
            <Search size={14} className="text-[var(--muted)]" />
            <input data-testid={`${testid}-search`} value={q} onChange={(e) => { setQ(e.target.value); setPage(0); }} placeholder="Search…" className="bg-transparent outline-none text-sm w-full" />
          </label>
        )}
        {filters}
        <span className="text-xs text-[var(--muted)] num ml-auto">{data.length.toLocaleString()} rows</span>
        {csvName && <Btn icon={Download} testid={`${testid}-csv`} onClick={() => downloadCSV(data, cols, csvName)}>CSV</Btn>}
      </div>
      <div className="overflow-auto max-h-[640px] border border-[var(--line)] rounded-sm">
        <table className="dt w-full text-sm">
          <thead>
            <tr>
              {cols.map((c) => (
                <th key={c.key} onClick={() => setSort({ key: c.key, dir: sort?.key === c.key && sort.dir === "desc" ? "asc" : "desc" })}
                  className={`px-3 py-2 text-[10px] uppercase tracking-wider text-[var(--muted)] font-medium cursor-pointer select-none whitespace-nowrap ${c.num ? "text-right" : "text-left"}`}
                  data-testid={`${testid}-sort-${c.key}`}>
                  <span className="inline-flex items-center gap-1">{c.label}{sort?.key === c.key && (sort.dir === "asc" ? <ArrowUp size={10} /> : <ArrowDown size={10} />)}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {view.map((r, i) => (
              <tr key={i} onClick={() => onRow && onRow(r)} className={`border-t border-[var(--line)] ${onRow ? "cursor-pointer" : ""}`} data-testid={`${testid}-row-${i}`}>
                {cols.map((c) => (
                  <td key={c.key} className={`px-3 py-2 whitespace-nowrap ${c.num ? "text-right num" : ""}`}>{c.render ? c.render(r) : r[c.key] ?? "–"}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pages > 1 && (
        <div className="flex items-center gap-2 mt-3 text-xs">
          <Btn testid={`${testid}-prev`} onClick={() => setPage(Math.max(0, page - 1))}>Prev</Btn>
          <span className="num text-[var(--muted)]">{page + 1} / {pages}</span>
          <Btn testid={`${testid}-next`} onClick={() => setPage(Math.min(pages - 1, page + 1))}>Next</Btn>
        </div>
      )}
    </div>
  );
}

export const Loading = ({ q, children }) => {
  if (q.isLoading) return <div className="text-[var(--muted)] text-sm py-20 text-center" data-testid="loading">Loading analysis…</div>;
  if (q.isError) return <div className="text-red-300 text-sm py-20 text-center" data-testid="load-error">Could not load data: {String(q.error?.message)}</div>;
  if (q.data === undefined || q.data === null) return <div className="text-amber-300 text-sm py-20 text-center" data-testid="empty-data">The API returned no dataset. Upload the official data pack or generate the analytics outputs, then refresh.</div>;
  return children(q.data);
};

export const Formula = ({ children }) => (
  <code className="block num text-[12px] bg-[var(--bg)] border border-[var(--line)] rounded-sm px-3 py-2 text-[var(--gold)] whitespace-pre-wrap">{children}</code>
);

export const KV = ({ rows }) => (
  <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 text-sm">
    {rows.map(([k, v]) => (<Fragment key={k}><dt className="text-[var(--muted)]">{k}</dt><dd className="num text-white">{String(v ?? "–")}</dd></Fragment>))}
  </dl>
);
