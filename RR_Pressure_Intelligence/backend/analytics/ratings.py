"""Player universe, eligibility, batting & bowling pressure ratings, validation and evidence."""
import numpy as np
import pandas as pd
from scipy import stats

BAT_COLS = dict(id="striker_id", tier="bat_tier", rv="rv_bat", mask="faced")
BOWL_COLS = dict(id="bowler_id", tier="bowl_tier", rv="rv_bowl", mask=None)
WEIGHTS = {"quality": 0.5, "delta": 0.25, "consistency": 0.25}


def player_universe(d, b):
    mp, p11, c = d["competition_team_player_mapping"], d["playing_eleven"], d["competitions"]
    c = c.assign(group=np.where(c.comp_name.str.contains("IPL"), "IPL", np.where(c.match_format == "T20I", "T20I", "Emerging")))
    names = pd.concat([mp[["player_id", "player_name"]],
                       b[["striker_id", "striker_name"]].set_axis(["player_id", "player_name"], axis=1),
                       b[["bowler_id", "bowler_name"]].set_axis(["player_id", "player_name"], axis=1)]).drop_duplicates("player_id")
    sources = {"mapping": set(mp.player_id), "playing_xi": set(p11.player_id), "deliveries": set(b.striker_id) | set(b.bowler_id) | set(b.non_striker_id)}
    pm = p11[p11.is_played.astype(bool)].merge(d["matches"][["match_id", "comp_id"]], on="match_id").merge(c[["comp_id", "group", "season"]], on="comp_id")
    played = pm.groupby(["player_id", "group"]).match_id.nunique().unstack(fill_value=0)
    teams = mp.groupby("player_id").team_name.apply(lambda s: sorted(set(s)))
    comps = mp.merge(c[["comp_id", "group", "season"]], on="comp_id").groupby("player_id").agg(
        n_comps=("comp_id", "nunique"), seasons=("season", lambda s: sorted(set(map(str, s)))))
    balls_f = b[b.faced].groupby("striker_id").size()
    balls_b = b[b.legal].groupby("bowler_id").size()
    u = names.set_index("player_id")
    for g in ["IPL", "T20I", "Emerging"]:
        u[f"{g.lower()}_matches"] = played.get(g, pd.Series(dtype=int)).reindex(u.index).fillna(0).astype(int)
    u["teams"] = teams.reindex(u.index)
    u["teams"] = u.teams.apply(lambda x: x if isinstance(x, list) else [])
    u = u.join(comps)
    u["n_comps"] = u.n_comps.fillna(0).astype(int)
    u["seasons"] = u.seasons.apply(lambda x: x if isinstance(x, list) else [])
    u["balls_faced"] = balls_f.reindex(u.index).fillna(0).astype(int)
    u["balls_bowled"] = balls_b.reindex(u.index).fillna(0).astype(int)
    u["in_sources"] = [", ".join(k for k, s in sources.items() if pid in s) for pid in u.index]
    # Data-provable cap: an appearance in a full T20 International. Absence of a T20I does NOT prove uncapped status.
    u["capped_in_data"] = u.t20i_matches > 0
    u["uncapped_status"] = np.where(u.capped_in_data, "Capped (T20I in supplied data)", "No cap found in supplied data (not externally verified)")
    u["eligibility_uncapped_lens"] = np.where(u.capped_in_data, "Ineligible", "Unverified")
    u["eligibility_official"] = "Eligible"  # PDF scope: all IPL & T20I players in the data pack
    u["domestic_status"] = np.where(u.ipl_matches + u.emerging_matches > 0, "Franchise/Emerging (no state-domestic data)", "International only")
    u["domestic_stats"] = "Missing (SMAT/Vijay Hazare/Ranji not in data pack)"
    u.index.name = "player_id"
    return u.reset_index()


def _eb_k(sums, n, sq):
    """Method-of-moments empirical-Bayes prior strength k = sigma^2_within / tau^2_between."""
    mask = n >= 100
    mean = sums[mask] / n[mask]
    sig_i = sq[mask] / n[mask] - mean ** 2
    sigma2 = float(np.average(sig_i, weights=n[mask]))
    tau2 = max(float(np.var(mean, ddof=1) - np.mean(sig_i / n[mask])), 1e-6)
    return float(sigma2 / tau2), float(sigma2), float(tau2)


def aggregate(b, cols):
    x = b if cols["mask"] is None else b[b[cols["mask"]]]
    x = x.assign(pid=x[cols["id"]], tier=x[cols["tier"]], rv=x[cols["rv"]])
    x = x.assign(press=x.tier != "Normal", rv2=x.rv ** 2, wrv=x.rv * x.LI)
    return x


def innings_table(x, disc):
    key = ["pid", "match_id", "innings"]
    p = x[x.press]
    inn = p.groupby(key).agg(pb=("rv", "size"), prv=("rv", "sum")).reset_index()
    inn = inn[inn.pb >= 6]
    inn["success"] = inn.prv >= 0
    return inn


def rate(x, inn, k_min_override=None, weights=WEIGHTS, min_pinn=8, sample_scale=1.0, disc="bat"):
    g = x.groupby(["pid", "press"]).agg(n=("rv", "size"), s=("rv", "sum"), sq=("rv2", "sum"), ws=("wrv", "sum"), wl=("LI", "sum")).unstack(fill_value=0)
    n_p, s_p, sq_p = g[("n", True)].values.astype(float), g[("s", True)].values, g[("sq", True)].values
    n_n, s_n, sq_n = g[("n", False)].values.astype(float), g[("s", False)].values, g[("sq", False)].values
    k_p, sig_p, tau_p = _eb_k(s_p, n_p, sq_p)
    k_n, _, _ = _eb_k(s_n, n_n, sq_n)
    r = pd.DataFrame(index=g.index)
    r["press_balls"], r["normal_balls"] = n_p, n_n
    r["press_rv100_raw"] = np.where(n_p > 0, s_p / np.maximum(n_p, 1) * 100, np.nan)
    r["normal_rv100_raw"] = np.where(n_n > 0, s_n / np.maximum(n_n, 1) * 100, np.nan)
    r["press_rv100_li"] = g[("ws", True)].values / np.maximum(g[("wl", True)].values, 1e-9) * 100
    r["quality"] = s_p / (n_p + k_p) * 100
    r["baseline"] = s_n / (n_n + k_n) * 100
    r["delta"] = r.quality - r.baseline
    r["reliability"] = n_p / (n_p + k_p)
    sd = np.sqrt(np.maximum(sq_p / np.maximum(n_p, 1) - (s_p / np.maximum(n_p, 1)) ** 2, 1e-9))
    r["ci_low"] = r.press_rv100_raw - 1.645 * sd / np.sqrt(np.maximum(n_p, 1)) * 100
    r["ci_high"] = r.press_rv100_raw + 1.645 * sd / np.sqrt(np.maximum(n_p, 1)) * 100
    ic = inn.groupby("pid").agg(p_inn=("success", "size"), p_succ=("success", "sum"), inn_sd=("prv", "std"))
    r = r.join(ic)
    r[["p_inn", "p_succ"]] = r[["p_inn", "p_succ"]].fillna(0)
    league = inn.success.mean()
    r["consistency"] = (r.p_succ + 10 * league) / (r.p_inn + 10)
    # Minimum sample: reliability n/(n+k) >= 0.20  =>  n >= k/4
    n_min = int(np.ceil((k_min_override or k_p) / 4 * sample_scale))
    r["qualified"] = (r.press_balls >= n_min) & (r.p_inn >= min_pinn)
    q = r[r.qualified]
    z = lambda s: (s - q[s.name].mean()) / q[s.name].std()
    comp = weights["quality"] * z(r.quality) + weights["delta"] * z(r.delta) + weights["consistency"] * z(r.consistency)
    r["rating"] = 50 + 10 * comp
    r["rank"] = r.rating.where(r.qualified).rank(ascending=False, method="first")
    meta = {"k_pressure": round(k_p, 1), "k_normal": round(k_n, 1), "sigma2": round(sig_p, 3), "tau2": round(tau_p, 5),
            "n_min_pressure_balls": n_min, "min_pressure_innings": min_pinn, "league_innings_success": round(float(league), 3),
            "n_qualified": int(r.qualified.sum())}
    return r, meta


def tier_stats(x, disc):
    if disc == "bat":
        agg = x.groupby(["pid", "tier"]).agg(balls=("rv", "size"), runs=("runs", "sum"), outs=("striker_out", "sum"),
                                             fours=("four", "sum"), sixes=("six", "sum"), dots=("runs", lambda s: int((s == 0).sum())), rv=("rv", "sum"))
        agg["sr"] = agg.runs / agg.balls * 100
        agg["avg"] = agg.runs / agg.outs.replace(0, np.nan)
        agg["bdry_pct"] = (agg.fours + agg.sixes) / agg.balls * 100
    else:
        agg = x.groupby(["pid", "tier"]).agg(deliveries=("rv", "size"), balls=("legal", "sum"), runs=("conceded", "sum"), wkts=("bowler_wkt", "sum"),
                                             fours=("four", "sum"), sixes=("six", "sum"), dots=("conceded", lambda s: int((s == 0).sum())), rv=("rv", "sum"))
        agg["econ"] = agg.runs / agg.balls * 6
        agg["avg"] = agg.runs / agg.wkts.replace(0, np.nan)
        agg["sr"] = agg.balls / agg.wkts.replace(0, np.nan)
        agg["bdry_pct"] = (agg.fours + agg.sixes) / agg.deliveries * 100
    agg["dot_pct"] = agg.dots / agg["balls" if disc == "bat" else "deliveries"] * 100
    agg["rv100"] = agg.rv / agg["balls" if disc == "bat" else "deliveries"] * 100
    return agg


def group_stats(x, disc, by):
    t = x.assign(tier=x[by] + "|" + np.where(x.press, "Pressure", "Normal"))
    return tier_stats(t, disc)


def roles(b, x, disc):
    if disc == "bat":
        pos = x.groupby(["pid", "match_id", "innings"]).batting_order.first().groupby("pid").median()
        role = pd.cut(pos, [0, 2, 3, 5, 7, 12], labels=["Opener", "Top order", "Middle order", "Finisher", "Lower order"]).astype(str)
        return pd.DataFrame({"role": role, "avg_position": pos.round(1)})
    sh = x[x.legal].groupby(["pid", "phase"]).size().unstack(fill_value=0)
    sh = sh.div(sh.sum(axis=1), axis=0)
    lab = {"Powerplay": "Powerplay specialist", "Middle": "Middle-overs specialist", "Death": "Death-overs specialist"}
    role = sh.apply(lambda r: lab[r.idxmax()] if r.max() >= 0.5 else ("Versatile (3-phase)" if (r >= 0.2).all() else "Multi-phase"), axis=1)
    btype = x.groupby("pid").bowling_type.agg(lambda s: s.mode().iat[0] if len(s.mode()) else "")
    pace = x.groupby("pid").pace_or_spin.agg(lambda s: s.mode().iat[0] if len(s.mode()) else "")
    return pd.DataFrame({"role": role, "pp_share": sh.get("Powerplay"), "mid_share": sh.get("Middle"), "death_share": sh.get("Death"),
                         "bowling_type": btype, "pace_spin": pace})


def bootstrap_ranks(x, inn, r, meta, weights=WEIGHTS, reps=300, seed=7):
    """Resample matches with replacement; recompute shrunk components and ratings for qualified players."""
    rng = np.random.default_rng(seed)
    qids = r.index[r.qualified]
    xs = x[x.pid.isin(qids)]
    mids = np.sort(x.match_id.unique())
    mi = {m: i for i, m in enumerate(mids)}
    pi = {p: i for i, p in enumerate(qids)}
    P, M = len(qids), len(mids)

    def mat(df, val):
        A = np.zeros((P, M))
        gg = df.groupby(["pid", "match_id"])[val].sum() if val else df.groupby(["pid", "match_id"]).size()
        for (p, m), v in gg.items():
            A[pi[p], mi[m]] = v
        return A
    xp, xn = xs[xs.press], xs[~xs.press]
    Sp, Np, Sn, Nn = mat(xp, "rv"), mat(xp, None), mat(xn, "rv"), mat(xn, None)
    ii = inn[inn.pid.isin(qids)]
    Ip, Is = mat(ii, None), mat(ii.assign(s=ii.success.astype(float)), "s")
    kp, kn, lg = meta["k_pressure"], meta["k_normal"], meta["league_innings_success"]
    ranks = np.zeros((reps, P))
    for t in range(reps):
        w = rng.multinomial(M, np.ones(M) / M).astype(float)
        sp, np_, sn, nn, ip, is_ = Sp @ w, Np @ w, Sn @ w, Nn @ w, Ip @ w, Is @ w
        qv = sp / (np_ + kp) * 100
        dv = qv - sn / (nn + kn) * 100
        cv = (is_ + 10 * lg) / (ip + 10)
        zz = lambda a: (a - a.mean()) / (a.std() + 1e-9)
        sc = weights["quality"] * zz(qv) + weights["delta"] * zz(dv) + weights["consistency"] * zz(cv)
        ranks[t] = stats.rankdata(-sc)
    return pd.DataFrame({"boot_median_rank": np.median(ranks, 0), "boot_rank_p05": np.percentile(ranks, 5, 0),
                         "boot_rank_p95": np.percentile(ranks, 95, 0), "boot_top10_pct": (ranks <= 10).mean(0) * 100}, index=qids)


def weight_sensitivity(r):
    q = r[r.qualified]
    z = {c: (q[c] - q[c].mean()) / q[c].std() for c in ["quality", "delta", "consistency"]}
    grid, counts = [], pd.Series(0, index=q.index, dtype=float)
    for wq in [0.34, 0.4, 0.5, 0.6, 0.7]:
        for share in [0.3, 0.5, 0.7]:
            wd, wc = (1 - wq) * share, (1 - wq) * (1 - share)
            sc = wq * z["quality"] + wd * z["delta"] + wc * z["consistency"]
            top = sc.sort_values(ascending=False).index[:10]
            counts[top] += 1
            grid.append({"w_quality": wq, "w_delta": round(wd, 3), "w_consistency": round(wc, 3),
                         "spearman_vs_base": round(float(stats.spearmanr(sc, q.rating).statistic), 3),
                         "top10_overlap": int(len(set(top) & set(q.rating.sort_values(ascending=False).index[:10])))})
    return grid, (counts / len(grid) * 100)


def temporal_stability(x):
    """Is pressure performance a repeatable trait? Correlate raw pressure RV/100 in 2022-24 vs 2025-26."""
    p = x[x.press]
    e1 = p[p.season_year <= 2024].groupby("pid").rv.agg(["sum", "size"])
    e2 = p[p.season_year >= 2025].groupby("pid").rv.agg(["sum", "size"])
    j = e1.join(e2, lsuffix="_a", rsuffix="_b", how="inner")
    j = j[(j.size_a >= 60) & (j.size_b >= 60)]
    a, c = j.sum_a / j.size_a, j.sum_b / j.size_b
    return {"players": int(len(j)), "pearson_r": round(float(stats.pearsonr(a, c).statistic), 3) if len(j) > 3 else None,
            "spearman_r": round(float(stats.spearmanr(a, c).statistic), 3) if len(j) > 3 else None}


def outlier_influence(x, inn, r, meta, weights=WEIGHTS):
    """Remove each qualified player's single best pressure innings and recompute their component values against fixed league z-params."""
    q = r[r.qualified]
    mu = {c: q[c].mean() for c in ["quality", "delta", "consistency"]}
    sd = {c: q[c].std() for c in ["quality", "delta", "consistency"]}
    best = inn[inn.pid.isin(q.index)].sort_values("prv", ascending=False).drop_duplicates("pid").set_index("pid")
    out = {}
    for pid, row in q.iterrows():
        if pid not in best.index:
            continue
        bi = best.loc[pid]
        s_p = row.quality * (row.press_balls + meta["k_pressure"]) / 100 - bi.prv
        n_p = row.press_balls - bi.pb
        qv = s_p / (n_p + meta["k_pressure"]) * 100
        dv = qv - row.baseline
        cv = (row.p_succ - 1 + 10 * meta["league_innings_success"]) / (row.p_inn - 1 + 10)
        out[pid] = 50 + 10 * (weights["quality"] * (qv - mu["quality"]) / sd["quality"] + weights["delta"] * (dv - mu["delta"]) / sd["delta"]
                              + weights["consistency"] * (cv - mu["consistency"]) / sd["consistency"])
    s = pd.Series(out)
    new_rank = s.rank(ascending=False)
    return pd.DataFrame({"rating_wo_best": s, "rank_wo_best": new_rank})


def match_evidence(x, pid, disc, k=6):
    p = x[x.pid == pid]
    key = ["match_id", "innings"]
    if disc == "bat":
        agg = p.groupby(key).agg(date=("match_date", "first"), comp=("comp_name", "first"), opp=("bowling_team_id", "first"),
                                 runs=("runs", "sum"), balls=("rv", "size"), outs=("striker_out", "sum"),
                                 press_balls=("press", "sum"), press_runs=("runs", lambda s: int(s[p.loc[s.index, "press"]].sum())),
                                 rv=("rv", "sum"), max_li=("LI", "max"), entry_score=("score", "first"), entry_wk=("wk", "first"),
                                 target=("target", "first"), entry_bl=("balls_left", "first"), result=("result", "first"))
    else:
        agg = p.groupby(key).agg(date=("match_date", "first"), comp=("comp_name", "first"), opp=("batting_team_id", "first"),
                                 runs=("conceded", "sum"), balls=("legal", "sum"), wkts=("bowler_wkt", "sum"),
                                 press_balls=("press", "sum"), press_runs=("conceded", lambda s: int(s[p.loc[s.index, "press"]].sum())),
                                 rv=("rv", "sum"), max_li=("LI", "max"), entry_score=("score", "first"), entry_wk=("wk", "first"),
                                 target=("target", "first"), entry_bl=("balls_left", "first"), result=("result", "first"))
    agg = agg[agg.press_balls >= 6].sort_values("rv", ascending=False)
    pick = pd.concat([agg.head(k), agg.tail(2)]) if len(agg) > k + 2 else agg
    return pick.reset_index().round(2).replace({np.nan: None}).to_dict("records"), int(len(agg))
