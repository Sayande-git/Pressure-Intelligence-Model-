import axios from "axios";
import { useQuery } from "@tanstack/react-query";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const useData = (name) =>
  useQuery({ queryKey: ["data", name], queryFn: () => axios.get(`${API}/data/${name}`).then((r) => r.data) });

export const useOverrides = () =>
  useQuery({ queryKey: ["overrides"], queryFn: () => axios.get(`${API}/eligibility/overrides`).then((r) => r.data) });

export const fmt = (v, d = 1) => (v === null || v === undefined || Number.isNaN(v) ? "–" : typeof v === "number" ? v.toFixed(d) : String(v));
export const int = (v) => (v === null || v === undefined ? "–" : Math.round(v).toLocaleString());
export const exportUrl = (f) => `${API}/export/${f}`;

export const downloadCSV = (rows, cols, name) => {
  const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const body = [cols.map((c) => esc(c.label)).join(","), ...rows.map((r) => cols.map((c) => esc(c.csv ? c.csv(r) : r[c.key])).join(","))].join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([body], { type: "text/csv" }));
  a.download = name;
  a.click();
};

export const uncappedLensStatus = (p, overrides) => {
  const o = overrides?.find((x) => x.player_id === p.player_id);
  if (o) return o.status;
  return p.capped_in_data ? "Ineligible" : "Unverified";
};
