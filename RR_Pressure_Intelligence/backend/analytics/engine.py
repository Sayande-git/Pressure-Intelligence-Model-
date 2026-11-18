"""Data ingestion, audit, match-state reconstruction, win-probability and pressure engine."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.preprocessing import StandardScaler

EXPECTED_FILES = ["ball_by_ball.csv", "matches.csv", "competitions.csv", "teams.csv",
                  "playing_eleven.csv", "competition_team_player_mapping.csv"]
ILLEGAL = {"wide", "Overstep", "other"}
PENALTY = {"wide": 1, "Overstep": 1, "other": 1, "byes": 1, "legbyes": 1, "Penalty": 5}
BOWLER_WKTS = {"Caught", "Bowled", "LBW", "Stump", "Hit Wicket"}
DOMESTIC_KEYWORDS = ["mushtaq", "hazare", "ranji", "duleep", "deodhar", "smat", "premier league t20 state"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def load(raw):
    raw = Path(raw)
    files = sorted(p.name for p in raw.glob("*.csv"))
    d = {f[:-4]: pd.read_csv(raw / f, low_memory=False) for f in files}
    fp = {f: sha(raw / f) for f in files}
    version = hashlib.sha256("".join(fp[f] for f in files).encode()).hexdigest()[:10]
    schema = {f[:-4]: list(d[f[:-4]].columns) for f in files}
    return d, {"files": files, "fingerprints": fp, "version": version, "schema": schema,
               "missing_expected": [f for f in EXPECTED_FILES if f not in files],
               "unexpected": [f for f in files if f not in EXPECTED_FILES],
               "non_csv": sorted(p.name for p in raw.iterdir() if p.suffix.lower() != ".csv")}


def audit(d):
    b, m, c, mp, p11 = d["ball_by_ball"], d["matches"], d["competitions"], d["competition_team_player_mapping"], d["playing_eleven"]
    tables = []
    for k, df in d.items():
        tables.append({"table": k, "rows": int(len(df)), "columns": int(df.shape[1]),
                       "duplicate_rows": int(df.duplicated().sum()),
                       "missing_cells": int(df.isna().sum().sum()),
                       "missing_by_column": {col: int(v) for col, v in df.isna().sum().items() if v > 0}})
    key_dupes = int(b.duplicated(["match_id", "innings", "overid", "over_ball_num"]).sum())
    m_ids, b_ids = set(m.match_id), set(b.match_id)
    res = m.result.fillna("")
    no_result = res.str.contains("(?i)abandon|no result")
    comp_names = " ".join(c.comp_name.str.lower())
    name_ids = mp.groupby("player_name").player_id.nunique()
    homonyms = sorted(name_ids[name_ids > 1].index.tolist())
    id_names = b.groupby("striker_id").striker_name.nunique()
    leg = b[b.innings <= 2]
    legal = ~leg.extras_type.isin(ILLEGAL)
    per_over = leg.assign(l=legal).groupby(["match_id", "innings", "overid"]).l.sum()
    return {
        "tables": tables,
        "delivery_key_duplicates": key_dupes,
        "matches_total": int(len(m)), "matches_with_deliveries": int(len(m_ids & b_ids)),
        "matches_without_deliveries": int(len(m_ids - b_ids)),
        "deliveries_without_match": int(len(b_ids - m_ids)),
        "abandoned_or_no_result": int(no_result.sum()),
        "matches_without_winner": int(m.win_team_id.isna().sum()),
        "rain_revised_matches": int(m.revised_target.notna().sum()),
        "super_over_deliveries": int((b.innings > 2).sum()),
        "super_over_matches": int(b[b.innings > 2].match_id.nunique()),
        "extras_breakdown": {str(k): int(v) for k, v in b.extras_type.fillna("none").value_counts().items()},
        "extras_encoding_note": "extras1_runs is a category code (6=none,2=wide,3=leg-bye,4=bye,1=no-ball,5=other), not a run count. Wide/no-ball/bye/leg-bye run values are not explicitly stored; one run per extra is assumed for team-total reconstruction only.",
        "dismissal_breakdown": {str(k): int(v) for k, v in b.dismissal_type.value_counts().items()},
        "legal_balls_per_over": {str(int(k)): int(v) for k, v in per_over.value_counts().sort_index().items()},
        "competitions_by_format": {str(k): int(v) for k, v in c.match_format.value_counts().items()},
        "seasons": {str(k): int(v) for k, v in c.season.astype(str).value_counts().sort_index().items()},
        "non_t20i_competitions": c[c.match_format != "T20I"].comp_name.tolist(),
        "domestic_competitions_found": [k for k in DOMESTIC_KEYWORDS if k in comp_names],
        "venue_countries": {str(k): int(v) for k, v in m.venue_country.value_counts().items()},
        "unique_venue_ids": int(m.venue_id.nunique()),
        "venue_name_available": "venue_name" in m.columns,
        "pitch_weather_boundary_fields": [col for col in m.columns if any(t in col.lower() for t in ["pitch", "weather", "dew", "boundary", "humid", "temp"])],
        "homonym_player_names": homonyms,
        "ids_with_multiple_names": int((id_names > 1).sum()),
        "playing_xi_is_played_false": int((~p11.is_played.astype(bool)).sum()),
        "impact_player_rows": int((p11.is_impact == 1).sum()),
    }


def comp_group(c):
    return np.where(c.comp_name.str.contains("IPL"), "IPL", np.where(c.match_format == "T20I", "T20I", "Emerging"))


def reconstruct(d):
    """Pre-delivery match state for innings 1-2 (super overs excluded). Uses only information known before each ball."""
    b = d["ball_by_ball"]
    b = b[b.innings <= 2].copy()
    m = d["matches"].copy()
    c = d["competitions"].copy()
    c["group"] = comp_group(c)
    m = m.merge(c[["comp_id", "comp_name", "match_format", "season", "group"]], on="comp_id", how="left")
    b = b.sort_values(["match_id", "innings", "overid", "over_ball_num"]).reset_index(drop=True)
    et = b.extras_type.fillna("none")
    b["legal"] = ~et.isin(ILLEGAL)
    b["faced"] = et != "wide"
    b["is_wicket"] = b.is_wicket.astype(str).str.lower() == "true"
    b["four"] = b.is_four.astype(str).str.lower() == "true"
    b["six"] = b.is_six.astype(str).str.lower() == "true"
    b["team_runs"] = b.runs + et.map(PENALTY).fillna(0) + b.extras_2_runs.fillna(0)
    pen_bowler = et.isin(["wide", "Overstep", "other"])
    b["conceded"] = b.runs + pen_bowler.astype(int) + np.where(pen_bowler, b.extras_2_runs.fillna(0), 0)
    b["bowler_wkt"] = b.is_wicket & b.dismissal_type.isin(BOWLER_WKTS)
    b["striker_out"] = b.is_wicket & (b.dismissed_player_id == b.striker_id)
    g = b.groupby(["match_id", "innings"])
    b["score"] = g.team_runs.cumsum() - b.team_runs
    b["wk"] = g.is_wicket.cumsum() - b.is_wicket
    b["legal_before"] = g.legal.cumsum() - b.legal
    totals = b.groupby(["match_id", "innings"]).team_runs.sum().unstack()
    m = m.set_index("match_id")
    m["inn1_total"] = totals.get(1)
    m["inn2_total"] = totals.get(2)
    m = m.reset_index()
    b = b.merge(m[["match_id", "comp_id", "comp_name", "group", "season", "match_date", "venue_id", "venue_country",
                   "first_inn_revised_overs", "second_inn_revised_overs", "revised_target", "inn1_total", "win_team_id", "result",
                   "home_team", "away_team"]], on="match_id", how="left")
    lim = np.where(b.innings == 1, b.first_inn_revised_overs, b.second_inn_revised_overs)
    b["ball_limit"] = pd.Series(lim).fillna(120).clip(upper=120).values
    b["balls_left"] = (b.ball_limit - b.legal_before).clip(lower=0)
    b["target"] = np.where(b.innings == 2, b.revised_target.fillna(b.inn1_total + 1), np.nan)
    b["req"] = b.target - b.score
    b["phase"] = np.select([b.overid <= 6, b.overid <= 15], ["Powerplay", "Middle"], "Death")
    b["wk_bucket"] = pd.cut(b.wk, [-1, 1, 3, 5, 10], labels=["0-1", "2-3", "4-5", "6+"]).astype(str)
    b["ipl"] = (b.group == "IPL").astype(int)
    res = b.result.fillna("")
    b["decided"] = b.win_team_id.notna() & ~res.str.contains("(?i)abandon|no result|tie")
    b["bat_won"] = (b.batting_team_id == b.win_team_id).astype(int)
    b["season_year"] = b.season.astype(str).str[:4].astype(int)
    return b, m


def _feat1(score, bl, wk, ipl):
    bl6 = bl / 6.0
    wl = 10 - wk
    return np.column_stack([score / 10, bl6, wk, wl * bl6, (score / 10) * (bl6 / 20), np.log1p(wl) * bl6, ipl])


def _feat2(req, bl, wk, ipl):
    bl = np.maximum(bl, 0)
    req = np.maximum(req, 0)
    wl = 10 - wk
    rrr = np.clip(req * 6 / np.maximum(bl, 1), 0, 36)
    return np.column_stack([rrr, wl, bl / 6, rrr * wl, np.log1p(req), np.log1p(wl) * bl / 6, req / np.maximum(bl, 1) * wl, ipl])


class WinProb:
    """Separate logistic win-probability models for setting (innings 1) and chasing (innings 2)."""

    def fit(self, b):
        t = b[b.decided]
        self.s1, self.s2 = StandardScaler(), StandardScaler()
        i1, i2 = t[t.innings == 1], t[t.innings == 2]
        X1 = self.s1.fit_transform(_feat1(i1.score.values, i1.balls_left.values, i1.wk.values, i1.ipl.values))
        X2 = self.s2.fit_transform(_feat2(i2.req.values, i2.balls_left.values, i2.wk.values, i2.ipl.values))
        self.m1 = LogisticRegression(max_iter=2000, C=1.0).fit(X1, i1.bat_won.values)
        self.m2 = LogisticRegression(max_iter=2000, C=1.0).fit(X2, i2.bat_won.values)
        return self

    def p1(self, score, bl, wk, ipl):
        p = self.m1.predict_proba(self.s1.transform(_feat1(score, bl, wk, ipl)))[:, 1]
        return np.where(wk >= 10, np.minimum(p, 0.5) * 0 + self.m1.predict_proba(self.s1.transform(_feat1(score, np.zeros_like(bl), np.minimum(wk, 9), ipl)))[:, 1], p)

    def p2(self, req, bl, wk, ipl):
        p = self.m2.predict_proba(self.s2.transform(_feat2(req, bl, np.minimum(wk, 9), ipl)))[:, 1]
        p = np.where(req <= 0, 1.0, p)
        p = np.where((req > 0) & ((wk >= 10) | (bl <= 0)), 0.0, p)
        return p

    def wp(self, inn, score, req, bl, wk, ipl):
        req = np.nan_to_num(np.asarray(req, dtype=float), nan=0.0)
        return np.where(inn == 1, self.p1(score, bl, wk, ipl), self.p2(req, bl, wk, ipl))


def validate_wp(b):
    """Time-based out-of-sample check: train <=2024, test 2025+."""
    t = b[b.decided]
    tr, te = t[t.season_year <= 2024], t[t.season_year >= 2025]
    wpm = WinProb().fit(tr)
    out = {}
    for inn in (1, 2):
        x = te[te.innings == inn]
        p = wpm.wp(x.innings.values, x.score.values, x.req.values, x.balls_left.values, x.wk.values, x.ipl.values)
        y = x.bat_won.values
        bins = pd.qcut(p, 10, duplicates="drop")
        cal = pd.DataFrame({"p": p, "y": y}).groupby(bins, observed=True).mean()
        out[f"innings_{inn}"] = {"n_test_deliveries": int(len(x)), "auc": round(float(roc_auc_score(y, p)), 3),
                                 "brier": round(float(brier_score_loss(y, p)), 3),
                                 "calibration": [{"pred": round(float(r.p), 3), "obs": round(float(r.y), 3)} for r in cal.itertuples()]}
    out["train_seasons"], out["test_seasons"] = "2022-2024", "2025-2026"
    return out, wpm


def add_pressure(b, wpm, q_mod=0.5, q_high=0.8):
    """Leverage = WP(after a boundary) - WP(after a wicket), from the pre-ball state. Normalised to mean 1 (Leverage Index)."""
    inn, s, r, bl, wk, ipl = b.innings.values, b.score.values, b.req.values, b.balls_left.values, b.wk.values, b.ipl.values
    if "wp_before" not in b:
        b["wp_before"] = wpm.wp(inn, s, r, bl, wk, ipl)
        bl1 = np.maximum(bl - 1, 0)
        wp4 = wpm.wp(inn, s + 4, r - 4, bl1, wk, ipl)
        wpw = wpm.wp(inn, s, r, bl1, np.minimum(wk + 1, 10), ipl)
        lev = np.clip(wp4 - wpw, 0, 1)
        b["LI"] = lev / lev.mean()
        tr = b.team_runs.values
        b["wp_after"] = wpm.wp(inn, s + tr, r - tr, np.where(b.legal, bl1, bl), wk + b.is_wicket.values, ipl)
    # Innings-specific cut-offs: setting and chasing leverage live on different scales, so tiers are relative within each innings.
    cuts = {}
    b["bat_tier"], b["bowl_tier"] = "Normal", "Normal"
    for inn in (1, 2):
        sel = b.innings == inn
        bc = b.loc[sel & b.faced, "LI"].quantile([q_mod, q_high]).values
        wc = b.loc[sel, "LI"].quantile([q_mod, q_high]).values
        b.loc[sel, "bat_tier"] = np.select([b.loc[sel, "LI"] >= bc[1], b.loc[sel, "LI"] >= bc[0]], ["High", "Moderate"], "Normal")
        b.loc[sel, "bowl_tier"] = np.select([b.loc[sel, "LI"] >= wc[1], b.loc[sel, "LI"] >= wc[0]], ["High", "Moderate"], "Normal")
        cuts[f"innings_{inn}"] = {"bat": [round(float(x), 3) for x in bc], "bowl": [round(float(x), 3) for x in wc]}
    return b, {"cutoffs": cuts, "q_mod": q_mod, "q_high": q_high}


def venue_factors(b, m):
    """Venue scoring factor = shrunk ratio of venue runs/ball to competition-group runs/ball. Applied only if venues differ significantly."""
    inn1 = m[m.inn1_total.notna() & ~m.result.fillna("").str.contains("(?i)abandon|no result")]
    inn1 = inn1[inn1.first_inn_revised_overs.isna()]
    vc = inn1.venue_id.value_counts()
    groups = [g.inn1_total.values for v, g in inn1[inn1.venue_id.isin(vc[vc >= 5].index)].groupby("venue_id")]
    kw = stats.kruskal(*groups)
    leg = b.groupby(["venue_id", "group"]).agg(runs=("team_runs", "sum"), balls=("legal", "sum"))
    grp = b.groupby("group").agg(runs=("team_runs", "sum"), balls=("legal", "sum"))
    leg["rpb"] = leg.runs / leg.balls
    leg["grp_rpb"] = grp.loc[leg.index.get_level_values(1)].eval("runs / balls").values
    k = 600.0  # prior strength in legal balls (~2.5 innings) for shrinkage toward 1.0
    leg["factor"] = (leg.runs + k * leg.grp_rpb) / ((leg.balls + k) * leg.grp_rpb)
    apply = bool(kw.pvalue < 0.05)
    fac = leg.factor.groupby(level=0).apply(lambda s: s.iloc[0]).to_dict() if False else {(v, g): f for (v, g), f in leg.factor.items()}
    b["venue_factor"] = [fac.get((v, g), 1.0) if apply else 1.0 for v, g in zip(b.venue_id, b.group)]
    return b, {"kruskal_H": round(float(kw.statistic), 2), "kruskal_p": float(f"{kw.pvalue:.3g}"), "venues_tested": len(groups),
               "adjustment_applied": apply, "shrinkage_prior_balls": k}


def expectations(b):
    """Context-expected outcomes per delivery from cells: competition group x innings x phase x wickets-lost x tier."""
    cells = ["group", "innings", "phase", "wk_bucket"]
    f = b[b.faced]
    # Run value of a wicket = drop in first-innings run expectancy RE(over, wickets) when one more wicket falls.
    i1 = b[(b.innings == 1) & b.first_inn_revised_overs.isna() & b.inn1_total.notna()]
    re_ = (i1.inn1_total - i1.score).groupby([i1.overid, i1.wk.clip(upper=9)]).agg(["mean", "size"])
    re_ = re_["mean"].where(re_["size"] >= 30).unstack()
    re_ = re_.interpolate(axis=1, limit_direction="both").ffill(axis=1)
    wv = (re_ - re_.shift(-1, axis=1)).clip(lower=1, upper=25)
    wv = wv.T.rolling(3, center=True, min_periods=1).mean().T.ffill(axis=1).fillna(1.0)
    wv = wv.stack().rename("W").reset_index().rename(columns={"wk": "wk_i"})
    b["wk_i"] = b.wk.clip(upper=9)
    bat = f.groupby(cells + ["bat_tier"]).agg(e_r=("runs", "mean"), p_w=("striker_out", "mean")).reset_index()
    bowl = b.groupby(cells + ["bowl_tier"]).agg(e_c=("conceded", "mean"), p_bw=("bowler_wkt", "mean")).reset_index()
    b = b.drop(columns=[c for c in ["e_r", "p_w", "W", "e_c", "p_bw"] if c in b], errors="ignore")
    b = b.merge(bat, on=cells + ["bat_tier"], how="left").merge(wv, on=["overid", "wk_i"], how="left").merge(bowl, on=cells + ["bowl_tier"], how="left")
    b["W"] = b.W.fillna(wv.W.median())
    vf = b.venue_factor
    b["rv_bat"] = np.where(b.faced, (b.runs - vf * b.e_r) - b.W * (b.striker_out.astype(float) - b.p_w), np.nan)
    b["rv_bowl"] = (vf * b.e_c - b.conceded) + b.W * (b.bowler_wkt.astype(float) - b.p_bw)
    return b, {"wicket_value_table": wv.round(2).to_dict("records")}


def pressure_summary(b):
    f = b[b.faced]
    rows = []
    for t in ["Normal", "Moderate", "High"]:
        x = f[f.bat_tier == t]
        m_close = x.groupby("match_id").size()
        rows.append({"tier": t, "balls": int(len(x)), "share": round(len(x) / len(f), 3),
                     "strike_rate": round(x.runs.sum() / len(x) * 100, 1),
                     "dismissal_pct": round(x.striker_out.mean() * 100, 2),
                     "dot_pct": round((x.runs == 0).mean() * 100, 1),
                     "boundary_pct": round((x.four | x.six).mean() * 100, 1),
                     "mean_LI": round(x.LI.mean(), 2),
                     "mean_wp_before": round(x.wp_before.mean(), 3),
                     "pct_innings2": round((x.innings == 2).mean() * 100, 1),
                     "pct_death": round((x.phase == "Death").mean() * 100, 1),
                     "matches": int(m_close.size)})
    phase = (f.groupby(["phase", "bat_tier"]).size().unstack(fill_value=0)).reset_index().to_dict("records")
    hist, edges = np.histogram(np.clip(b.LI, 0, 6), bins=30)
    heat = b[(b.innings == 2) & b.legal].assign(
        rrr_b=pd.cut(np.clip(b.req * 6 / np.maximum(b.balls_left, 1), 0, 30), [0, 6, 8, 10, 12, 15, 30], include_lowest=True).astype(str),
        bl_b=pd.cut(b.balls_left, [0, 18, 36, 60, 90, 120], include_lowest=True).astype(str)
    ).groupby(["rrr_b", "bl_b"]).LI.mean().round(2).reset_index().to_dict("records")
    wk_heat = f.groupby(["phase", "wk_bucket"]).LI.mean().round(2).reset_index().to_dict("records")
    # Close-finish validation: share of high-tier balls in matches decided by <=10 runs or <=2 wickets/<=6 balls not stored -> use margin parse.
    return {"tiers": rows, "phase_tier_counts": phase,
            "li_hist": [{"x": round(float(edges[i]), 2), "n": int(hist[i])} for i in range(len(hist))],
            "chase_heat": heat, "wicket_phase_heat": wk_heat}


def tier_separation(b):
    """Does the tiering separate genuinely tighter contests? Compare final-margin closeness across tiers."""
    m = b.drop_duplicates("match_id")[["match_id", "result"]].copy()
    m["runs_margin"] = m.result.str.extract(r"(?i)(\d+)\s*runs?")[0].astype(float)
    m["wkts_margin"] = m.result.str.extract(r"(?i)(\d+)\s*w(?:ic)?k")[0].astype(float)
    m["close"] = (m.runs_margin <= 15) | (m.wkts_margin <= 3)
    x = b[b.faced].merge(m[["match_id", "close"]], on="match_id")
    return {t: round(float(x[x.bat_tier == t].close.mean() * 100), 1) for t in ["Normal", "Moderate", "High"]}


def save_json(obj, path):
    Path(path).write_text(json.dumps(obj, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
