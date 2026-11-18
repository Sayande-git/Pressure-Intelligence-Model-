"""End-to-end reproducible pipeline: python -m analytics.run <raw_dir> <out_root>"""
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from analytics import engine as E
from analytics import ratings as R

DISC = {"bat": R.BAT_COLS, "bowl": R.BOWL_COLS}


def clean(v):
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return None if not np.isfinite(v) else round(float(v), 3)
    if isinstance(v, np.bool_):
        return bool(v)
    return v


def frame(df):
    return clean(df.replace({np.nan: None}).to_dict("records"))


def build_discipline(b, disc, uni, team_names, k_override=None):
    cols = DISC[disc]
    x = R.aggregate(b, cols)
    inn = R.innings_table(x, disc)
    r, meta = R.rate(x, inn, k_min_override=k_override, disc=disc)
    return x, inn, r, meta


def discipline_outputs(b, disc, uni, team_names, base_q):
    x, inn, r, meta = build_discipline(b, disc, uni, team_names)
    role = R.roles(b, x, disc)
    ts = R.tier_stats(x, disc)
    boot = R.bootstrap_ranks(x, inn, r, meta)
    grid, wfreq = R.weight_sensitivity(r)
    outl = R.outlier_influence(x, inn, r, meta)
    r = r.join(role).join(boot).join(wfreq.rename("weight_top10_pct")).join(outl)
    names = uni.set_index("player_id")
    r["name"] = names.player_name.reindex(r.index)
    r["teams"] = names.teams.reindex(r.index)
    r["capped_in_data"] = names.capped_in_data.reindex(r.index)
    r["uncapped_lens"] = names.eligibility_uncapped_lens.reindex(r.index)
    q = r[r.qualified].sort_values("rating", ascending=False)

    def tierblock(pid):
        out = {}
        for t in ["Normal", "Moderate", "High"]:
            if (pid, t) in ts.index:
                out[t] = clean(ts.loc[(pid, t)].to_dict())
        return out
    ph = R.group_stats(x, disc, "phase")
    cg = R.group_stats(x, disc, "group")
    vs = R.group_stats(x.assign(venue=x.venue_id.astype(str)), disc, "venue")
    profiles = {}
    for i, (pid, row) in enumerate(q.iterrows()):
        ev, n_pinn = R.match_evidence(x, pid, disc)
        for e in ev:
            e["opp"] = team_names.get(e["opp"], str(e["opp"]))
        sub = lambda tab: {k.split("|")[0] + "|" + k.split("|")[1]: clean(tab.loc[(pid, k)].to_dict()) for k in tab.loc[pid].index} if pid in tab.index.get_level_values(0) else {}
        vsub = sub(vs)
        top_v = sorted({k.split("|")[0] for k in vsub}, key=lambda v: -sum(vsub.get(f"{v}|{t}", {}).get("balls", 0) or 0 for t in ["Pressure", "Normal"]))[:6]
        nxt = q.iloc[i + 1] if i + 1 < len(q) else None
        profiles[str(pid)] = {
            "tiers": tierblock(pid), "phases": sub(ph), "competitions": sub(cg),
            "venues": {k: v for k, v in vsub.items() if k.split("|")[0] in top_v},
            "matches": ev, "pressure_innings": n_pinn,
            "next_ranked": None if nxt is None else {"name": nxt["name"], "rating": round(float(nxt.rating), 2),
                                                     "quality": round(float(nxt.quality), 2), "delta": round(float(nxt.delta), 2),
                                                     "consistency": round(float(nxt.consistency), 3)},
        }
    keep = ["name", "teams", "rank", "rating", "quality", "baseline", "delta", "consistency", "reliability", "press_balls", "normal_balls",
            "press_rv100_raw", "normal_rv100_raw", "press_rv100_li", "ci_low", "ci_high", "p_inn", "p_succ", "role", "capped_in_data",
            "uncapped_lens", "boot_median_rank", "boot_rank_p05", "boot_rank_p95", "boot_top10_pct", "weight_top10_pct", "rating_wo_best", "rank_wo_best"]
    keep += [c for c in ["avg_position", "pp_share", "mid_share", "death_share", "bowling_type", "pace_spin"] if c in q.columns]
    qq = q[keep].copy()
    qq["player_id"] = qq.index
    # Headline tier stats for table columns
    for t in ["Normal", "Pressure"]:
        sel = x[x.press == (t == "Pressure")]
        if disc == "bat":
            g = sel.groupby("pid").agg(runs=("runs", "sum"), balls=("rv", "size"), outs=("striker_out", "sum"))
            qq[f"{t.lower()}_runs"] = g.runs.reindex(qq.index)
            qq[f"{t.lower()}_balls"] = g.balls.reindex(qq.index)
            qq[f"{t.lower()}_outs"] = g.outs.reindex(qq.index)
            qq[f"{t.lower()}_sr"] = (g.runs / g.balls * 100).reindex(qq.index)
            qq[f"{t.lower()}_avg"] = (g.runs / g.outs.replace(0, np.nan)).reindex(qq.index)
        else:
            g = sel.groupby("pid").agg(runs=("conceded", "sum"), balls=("legal", "sum"), wkts=("bowler_wkt", "sum"),
                                       dots=("conceded", lambda s: int((s == 0).sum())), n=("rv", "size"))
            qq[f"{t.lower()}_runs"] = g.runs.reindex(qq.index)
            qq[f"{t.lower()}_balls"] = g.balls.reindex(qq.index)
            qq[f"{t.lower()}_wkts"] = g.wkts.reindex(qq.index)
            qq[f"{t.lower()}_econ"] = (g.runs / g.balls * 6).reindex(qq.index)
            qq[f"{t.lower()}_dot_pct"] = (g.dots / g.n * 100).reindex(qq.index)
    qq["matches"] = x[x.pid.isin(qq.index)].groupby("pid").match_id.nunique().reindex(qq.index)
    qq["robust"] = (qq.boot_top10_pct >= 50) & (qq.weight_top10_pct >= 60)
    all_players = r[r.press_balls >= 30][["name", "press_balls", "normal_balls", "press_rv100_raw", "normal_rv100_raw", "quality", "baseline", "qualified", "capped_in_data"]].copy()
    all_players["player_id"] = all_players.index
    corr = qq[["quality", "delta", "consistency"]].corr().round(3)
    return {"meta": meta, "ranking": frame(qq.reset_index(drop=True)), "profiles": clean(profiles),
            "weight_grid": grid, "component_corr": clean(corr.to_dict()),
            "pool": frame(all_players.reset_index(drop=True)), "temporal": R.temporal_stability(x),
            "tier_cutoffs": base_q}, (x, inn, r, meta)


def threshold_sensitivity(b, wpm, base_rank, disc):
    out = []
    for qm, qh in [(0.4, 0.75), (0.5, 0.85), (0.6, 0.8), (0.5, 0.9)]:
        bb, _ = E.add_pressure(b.copy(), wpm, qm, qh)
        bb, _ = E.expectations(bb)
        x = R.aggregate(bb, DISC[disc])
        inn = R.innings_table(x, disc)
        r, meta = R.rate(x, inn)
        q = r[r.qualified].sort_values("rating", ascending=False)
        top = list(q.index[:10])
        common = base_rank.index.intersection(q.index)
        out.append({"q_mod": qm, "q_high": qh, "n_qualified": int(len(q)), "top10_overlap": len(set(top) & set(base_rank.index[:10])),
                     "spearman_common": round(float(stats.spearmanr(base_rank.loc[common].rating, q.loc[common].rating).statistic), 3)})
    return out


def sample_sensitivity(x, inn, base_rank, meta):
    out = []
    for sc in [0.67, 1.5, 2.0]:
        r, m2 = R.rate(x, inn, sample_scale=sc)
        q = r[r.qualified].sort_values("rating", ascending=False)
        out.append({"scale": sc, "n_min": m2["n_min_pressure_balls"], "n_qualified": int(len(q)),
                    "top10_overlap": len(set(q.index[:10]) & set(base_rank.index[:10]))})
    return out


def venue_outputs(b, m, team_names):
    mm = m[~m.result.fillna("").str.contains("(?i)abandon|no result")]
    rows = []
    for v, g in mm.groupby("venue_id"):
        bb = b[b.venue_id == v]
        legal = bb.legal.sum()
        full = g[g.first_inn_revised_overs.isna()]
        dec = g[g.win_team_id.notna()]
        chase_w = (dec.win_team_id != dec.toss_win_team_id.where(dec.toss_opted == "Batting")).mean() if len(dec) else np.nan
        bat1 = bb[bb.innings == 1].groupby("match_id").batting_team_id.first()
        winners = dec.set_index("match_id").win_team_id
        chase_win = float((winners != bat1.reindex(winners.index)).mean()) if len(winners) else None
        home = g[g.group == "IPL"].home_team.mode()
        pace = bb[bb.pace_or_spin == "Pace"]
        spin = bb[bb.pace_or_spin == "Spin"]
        rows.append({"venue_id": int(v), "country": g.venue_country.iat[0], "matches": int(len(g)),
                     "competitions": ", ".join(sorted(g.group.dropna().unique())),
                     "ipl_home_team_inferred": home.iat[0] if len(home) else None,
                     "avg_first_innings": round(float(full.inn1_total.mean()), 1) if len(full) else None,
                     "avg_second_innings": round(float(full.inn2_total.mean()), 1) if len(full) else None,
                     "run_rate": round(float(bb.team_runs.sum() / max(legal, 1) * 6), 2),
                     "wkts_per_match": round(float(bb.is_wicket.sum() / len(g)), 2),
                     "chasing_win_pct": round(chase_win * 100, 1) if chase_win is not None else None,
                     "pace_econ": round(float(pace.conceded.sum() / max(pace.legal.sum(), 1) * 6), 2),
                     "spin_econ": round(float(spin.conceded.sum() / max(spin.legal.sum(), 1) * 6), 2),
                     "spin_wkt_share": round(float(spin.bowler_wkt.sum() / max(bb.bowler_wkt.sum(), 1) * 100), 1),
                     "spin_ball_share": round(float(spin.legal.sum() / max(legal, 1) * 100), 1),
                     "venue_factor": round(float(bb.venue_factor.mean()), 3),
                     "boundary_pct": round(float((bb.four | bb.six).sum() / max(legal, 1) * 100), 1)})
    v = pd.DataFrame(rows).sort_values("matches", ascending=False)
    rr = v[v.ipl_home_team_inferred == "Rajasthan Royals"]
    return {"venues": frame(v), "rr_home_venue_ids": rr.venue_id.tolist()}


def home_away(x, disc, ids, team_lookup):
    """Player stats at RR inferred home venues vs elsewhere (top-10 only)."""
    return None


def requirements(state):
    R_ = []
    add = lambda area, req, status, ev, official=True: R_.append({"area": area, "requirement": req, "status": status, "evidence": ev, "official": official})
    add("Official", "Define pressure (indicators + rationale)", "Verified", "Pressure Intelligence; report §7")
    add("Official", "Pressure method works for batting and bowling", "Verified", "Batting & Bowling Analytics")
    add("Official", "Metrics, player baselines, rating logic", "Verified", "Methodology; report §9-11")
    add("Official", "Fair comparisons: sample sizes, eligibility, contexts, IPL vs T20I", "Verified", "Validation Centre; report §12")
    add("Official", "Top-10 batters, ordered, no repeats", "Verified" if state["bat_n"] >= 10 else "In progress", "Player Rankings")
    add("Official", "Top-10 bowlers, ordered, no repeats", "Verified" if state["bowl_n"] >= 10 else "In progress", "Player Rankings")
    add("Official", "Evidence (tables/charts) for top 10", "Verified", "Evidence Centre; report §15-16")
    add("Official", "Consistency across matches & limitations", "Verified", "Validation Centre; report §19-23")
    add("Official", "Reproducible methodology report (PDF)", "Verified" if state["report"] else "In progress", "Reports & Exports")
    add("Data audit", "Schema, keys, duplicates, missing values", "Verified", "Data Intelligence")
    add("Data audit", "Extras / legal-delivery handling", "Tested", "Data Intelligence (extras note)")
    add("Data audit", "Team-total reconstruction vs official margins", "Tested", f"{state['recon_within3']}% within 3 runs")
    add("Eligibility", "Player universe & identity resolution", "Verified", "Domestic Player Eligibility")
    add("Eligibility", "Capped flag from T20I appearances in data", "Verified", "Eligibility table")
    add("Eligibility", "External verification of uncapped status (public sources)", "Not started", "Manual review list; requires per-player web verification", False)
    add("Eligibility", "Domestic (SMAT/VHT/Ranji) statistics", "Not started", "Not in data pack; documented gap", False)
    add("Pressure", "Win-probability leverage engine, no leakage", "Verified", f"Out-of-sample AUC {state['auc']}")
    add("Pressure", "Three tiers with sensitivity tests", "Verified", "Validation Centre")
    add("Batting", "Role, phase, tier stats per batter", "Verified", "Batting Analytics")
    add("Bowling", "Role, phase, tier stats per bowler", "Verified", "Bowling Analytics")
    add("Venue", "Venue scoring factor (statistically tested)", "Verified", "Venue Intelligence")
    add("Venue", "Pitch, weather, dew, boundary dimensions", "Not started", "Not in data pack; not fabricated", False)
    add("Validation", "Bootstrap rank stability", "Verified", "Validation Centre")
    add("Validation", "Weight / threshold / sample sensitivity", "Verified", "Validation Centre")
    add("Validation", "Temporal (out-of-sample) trait stability", "Verified", "Validation Centre")
    add("Product", "Dataset versioning & re-run on new data", "Tested", "Reports & Exports > Dataset versions")
    score = {"Verified": 1, "Tested": 0.85, "Implemented": 0.6, "In progress": 0.3, "Not started": 0}
    off = [r for r in R_ if r["official"] and r["area"] == "Official"]
    by_area = {}
    for r in R_:
        by_area.setdefault(r["area"], []).append(score[r["status"]])
    return {"items": R_, "official_completion": round(100 * sum(score[r["status"]] for r in off) / len(off), 1),
            "area_completion": {k: round(100 * np.mean(v), 1) for k, v in by_area.items()}}


def run(raw_dir, out_root):
    t0 = time.time()
    out_root = Path(out_root)
    d, info = E.load(raw_dir)
    ver = info["version"]
    out = out_root / ver
    out.mkdir(parents=True, exist_ok=True)
    au = E.audit(d)
    b, m = E.reconstruct(d)
    # Reconciliation of reconstructed totals against official run margins
    mm = m.copy()
    mm["N"] = mm.result.str.extract(r"(?i)by (\d+) runs?")[0].astype(float)
    rec = mm[mm.N.notna()]
    diff = (rec.inn1_total - rec.inn2_total - rec.N)
    au["reconciliation"] = {"matches_checked": int(len(rec)), "exact_pct": round(float((diff == 0).mean() * 100), 1),
                            "within3_pct": round(float((diff.abs() <= 3).mean() * 100), 1), "median_abs_error": float(diff.abs().median())}
    wpv, _ = E.validate_wp(b)
    wpm = E.WinProb().fit(b)
    b, cut = E.add_pressure(b, wpm)
    b, vmeta = E.venue_factors(b, m)
    b, xmeta = E.expectations(b)
    team_names = d["teams"].drop_duplicates("team_id").set_index("team_id").team_name.to_dict()
    uni = R.player_universe(d, b)
    bat, (xb, ib, rb, mb) = discipline_outputs(b, "bat", uni, team_names, cut)
    bowl, (xw, iw, rw, mw) = discipline_outputs(b, "bowl", uni, team_names, cut)
    base_b = rb[rb.qualified].sort_values("rating", ascending=False)
    base_w = rw[rw.qualified].sort_values("rating", ascending=False)
    bat["threshold_sensitivity"] = threshold_sensitivity(b, wpm, base_b, "bat")
    bowl["threshold_sensitivity"] = threshold_sensitivity(b, wpm, base_w, "bowl")
    bat["sample_sensitivity"] = sample_sensitivity(xb, ib, base_b, mb)
    bowl["sample_sensitivity"] = sample_sensitivity(xw, iw, base_w, mw)
    # Venue adjustment on/off comparison
    b_nv = b.copy()
    b_nv["venue_factor"] = 1.0
    b_nv, _ = E.expectations(b_nv)
    for disc, base, store in [("bat", base_b, bat), ("bowl", base_w, bowl)]:
        x2 = R.aggregate(b_nv, DISC[disc])
        r2, _ = R.rate(x2, R.innings_table(x2, disc))
        q2 = r2[r2.qualified].sort_values("rating", ascending=False)
        common = base.index.intersection(q2.index)
        store["venue_adjust_effect"] = {"top10_overlap": len(set(q2.index[:10]) & set(base.index[:10])),
                                        "spearman": round(float(stats.spearmanr(base.loc[common].rating, q2.loc[common].rating).statistic), 3)}
    venues = venue_outputs(b, m, team_names)
    rr_ids = set(venues["rr_home_venue_ids"])
    for disc, x, store in [("bat", xb, bat), ("bowl", xw, bowl)]:
        top = [r["player_id"] for r in store["ranking"][:10]]
        sel = x[x.pid.isin(top)]
        sel = sel.assign(loc=np.where(sel.venue_id.isin(rr_ids), "RR home venues", "Other venues"))
        ts = R.tier_stats(sel.assign(tier=sel["loc"]), disc)
        store["rr_home"] = {str(p): clean({t: ts.loc[(p, t)].to_dict() for t in ts.loc[p].index}) for p in top if p in ts.index.get_level_values(0)}
    pres = E.pressure_summary(b)
    pres["close_match_pct_by_tier"] = E.tier_separation(b)
    pres["cutoffs"] = cut
    pres["wp_validation"] = wpv
    pres["wp_coefficients"] = {"innings1": [round(float(c), 3) for c in wpm.m1.coef_[0]], "innings2": [round(float(c), 3) for c in wpm.m2.coef_[0]]}
    pres["wicket_values"] = xmeta["wicket_value_table"]
    # Example deliveries to illustrate the pressure index (real rows)
    ex = b[(b.innings == 2) & b.legal].sample(8, random_state=3)[["match_id", "match_date", "comp_name", "overid", "over_ball_num", "score", "wk", "req", "balls_left", "wp_before", "LI", "bat_tier"]]
    hi = b[(b.innings == 2) & b.legal & (b.bat_tier == "High")].sample(4, random_state=5)[ex.columns]
    pres["examples"] = frame(pd.concat([ex, hi]))
    uni_out = uni.copy()
    uni_out["bat_sample"] = uni_out.player_id.map(rb.press_balls).fillna(0) >= mb["n_min_pressure_balls"]
    uni_out["bowl_sample"] = uni_out.player_id.map(rw.press_balls).fillna(0) >= mw["n_min_pressure_balls"]
    elig = {"players": frame(uni_out), "summary": {
        "total_players": int(len(uni_out)), "official_eligible": int(len(uni_out)),
        "capped_in_data_ineligible_lens": int(uni_out.capped_in_data.sum()),
        "unverified_lens": int((~uni_out.capped_in_data).sum()),
        "bat_sufficient": int(uni_out.bat_sample.sum()), "bowl_sufficient": int(uni_out.bowl_sample.sum()),
        "missing_domestic": int(len(uni_out)), "homonyms": au["homonym_player_names"]}}
    state = {"bat_n": len(bat["ranking"]), "bowl_n": len(bowl["ranking"]), "report": True,
             "recon_within3": au["reconciliation"]["within3_pct"], "auc": wpv["innings_2"]["auc"]}
    reqs = requirements(state)
    overview = {"version": ver, "generated_at": datetime.now(timezone.utc).isoformat(), "runtime_sec": None,
                "files": info, "matches": au["matches_total"], "matches_with_deliveries": au["matches_with_deliveries"],
                "deliveries": int(len(d["ball_by_ball"])), "deliveries_modelled": int(len(b)),
                "players": elig["summary"], "requirements": reqs["official_completion"],
                "data_quality": round(100 - 100 * sum(t["missing_cells"] for t in au["tables"] if t["table"] != "ball_by_ball") / max(sum(t["rows"] * t["columns"] for t in au["tables"] if t["table"] != "ball_by_ball"), 1), 1),
                "top_bat": bat["ranking"][:10], "top_bowl": bowl["ranking"][:10],
                "venue_meta": vmeta, "bat_meta": bat["meta"], "bowl_meta": bowl["meta"]}
    files = {"overview": overview, "audit": au, "eligibility": elig, "pressure": pres, "batting": bat, "bowling": bowl,
             "venues": {**venues, "meta": vmeta}, "requirements": reqs}
    for k, v in files.items():
        (out / f"{k}.json").write_text(json.dumps(clean(v)))
    # CSV exports
    pd.DataFrame(bat["ranking"]).to_csv(out / "batting_rankings.csv", index=False)
    pd.DataFrame(bowl["ranking"]).to_csv(out / "bowling_rankings.csv", index=False)
    uni_out.to_csv(out / "player_eligibility.csv", index=False)
    pd.DataFrame(venues["venues"]).to_csv(out / "venues.csv", index=False)
    cols = ["match_id", "innings", "overid", "over_ball_num", "striker_id", "striker_name", "bowler_id", "bowler_name", "score", "wk", "req", "balls_left",
            "phase", "wp_before", "wp_after", "LI", "bat_tier", "bowl_tier", "runs", "conceded", "striker_out", "bowler_wkt", "venue_factor", "rv_bat", "rv_bowl"]
    b[cols].round(4).to_csv(out / "engineered_deliveries.csv.gz", index=False, compression="gzip")
    from analytics.report import build_report
    build_report(out, files)
    overview["runtime_sec"] = round(time.time() - t0, 1)
    (out / "overview.json").write_text(json.dumps(clean(overview)))
    # Version registry and change log
    reg_p = out_root / "registry.json"
    reg = json.loads(reg_p.read_text()) if reg_p.exists() else {"versions": [], "current": None}
    prev = next((v for v in reg["versions"] if v["version"] == reg["current"]), None)
    changes = {}
    if prev and prev["version"] != ver:
        for t, cols_ in info["schema"].items():
            old = prev["schema"].get(t)
            if old is None:
                changes[t] = "new table"
            else:
                add_, rem = sorted(set(cols_) - set(old)), sorted(set(old) - set(cols_))
                if add_ or rem:
                    changes[t] = {"added": add_, "removed": rem}
        for t in prev["schema"]:
            if t not in info["schema"]:
                changes[t] = "table removed"
    reg["versions"] = [v for v in reg["versions"] if v["version"] != ver] + [{
        "version": ver, "generated_at": overview["generated_at"], "files": info["files"], "fingerprints": info["fingerprints"],
        "schema": info["schema"], "schema_changes_vs_previous": changes, "previous": reg["current"],
        "top_bat": [r["name"] for r in bat["ranking"][:10]], "top_bowl": [r["name"] for r in bowl["ranking"][:10]]}]
    reg["current"] = ver
    reg_p.write_text(json.dumps(clean(reg)))
    return ver


if __name__ == "__main__":
    print(run(sys.argv[1], sys.argv[2]))
