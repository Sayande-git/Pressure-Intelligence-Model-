"""Franchise methodology report (PDF) generated directly from pipeline outputs."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

PURPLE, GOLD, NAVY = "#5B2A86", "#C9A227", "#0F1729"
ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=ss["Heading1"], textColor=colors.HexColor(PURPLE), fontSize=15, spaceAfter=6)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=colors.HexColor(NAVY), fontSize=11.5, spaceAfter=4)
P = ParagraphStyle("p", parent=ss["BodyText"], fontSize=8.8, leading=12)
SM = ParagraphStyle("sm", parent=P, fontSize=7.2, leading=9)


def f(v, d=1):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.{d}f}"
    return str(v)


def tbl(rows, widths=None, font=7.2):
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONTSIZE", (0, 0), (-1, -1), font), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8BCC8")),
                           ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F0F8")]),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    return t


def chart(path, fn, w=16, h=6):
    fig, ax = plt.subplots(figsize=(w / 2.54, h / 2.54), dpi=150)
    fn(ax)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=6)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return Image(str(path), width=w * cm, height=h * cm)


def i_(v):
    return "-" if v is None else int(v)


def build_report(out, F):
    out = Path(out)
    ov, au, el, pr, bat, bowl, ven, rq = (F[k] for k in ["overview", "audit", "eligibility", "pressure", "batting", "bowling", "venues", "requirements"])
    S = []
    add = S.append
    sec = lambda n, t: add(Paragraph(f"{n}. {t}", H1))
    para = lambda t: add(Paragraph(t, P))
    bm, wm = bat["meta"], bowl["meta"]
    tb, tw = bat["ranking"][:10], bowl["ranking"][:10]

    add(Paragraph("Rajasthan Royals | SupeRR Selector S2 | Round 1", ParagraphStyle("k", parent=P, textColor=colors.HexColor(GOLD))))
    add(Paragraph("Pressure Intelligence: Most Reliable Players Under Pressure", ParagraphStyle("t", parent=H1, fontSize=20, leading=24)))
    para(f"Dataset version <b>{ov['version']}</b> | generated {ov['generated_at'][:19]} UTC | {ov['deliveries']:,} deliveries, {ov['matches']} matches. "
         "All figures are computed by the reproducible pipeline <i>analytics/run.py</i> from the supplied data pack; no statistic is entered by hand.")

    sec(1, "Executive Summary")
    para("Pressure is defined as <b>win-probability leverage</b>: for every delivery, how far the match swings between a good batting outcome (a boundary) and a good bowling outcome (a wicket), "
         "computed only from the pre-delivery state (runs, wickets, balls left, target). Players are rated on <b>runs value above context expectation</b> under pressure, "
         "relative to their own normal baseline, with empirical-Bayes shrinkage for sample size and a consistency term across pressure innings.")
    add(tbl([["#", "Top-10 batters", "Rating", "#", "Top-10 bowlers", "Rating"]] +
            [[i + 1, tb[i]["name"], f(tb[i]["rating"]), i + 1, tw[i]["name"], f(tw[i]["rating"])] for i in range(min(10, len(tb), len(tw)))],
            [1 * cm, 5.2 * cm, 1.8 * cm, 1 * cm, 5.2 * cm, 1.8 * cm], 8))
    sec(2, "Challenge Objective")
    para("Build a data-driven system measuring how batters and bowlers perform in high-pressure situations compared with their usual levels; rank the 10 most reliable batters and bowlers; "
         "document pressure definition, metrics, baselines, fair-comparison rules, evidence, reliability and limitations (official Round 1 PDF).")
    sec(3, "Data Sources and Dataset Overview")
    add(tbl([["Table", "Rows", "Cols", "Dup rows", "Missing cells"]] + [[t["table"], f"{t['rows']:,}", t["columns"], t["duplicate_rows"], f"{t['missing_cells']:,}"] for t in au["tables"]]))
    para(f"Formats: {au['competitions_by_format']}. Non-T20I competitions: {', '.join(au['non_t20i_competitions'])}.")
    sec(4, "Data Quality Audit")
    rc = au["reconciliation"]
    add(tbl([["Check", "Result"],
             ["Delivery key duplicates", au["delivery_key_duplicates"]], ["Matches without deliveries", au["matches_without_deliveries"]],
             ["Abandoned / no result", au["abandoned_or_no_result"]], ["Rain-revised targets", au["rain_revised_matches"]],
             ["Super-over deliveries (excluded)", au["super_over_deliveries"]], ["Player names with >1 ID (homonyms)", len(au["homonym_player_names"])],
             ["Run-margin reconciliation (matches)", rc["matches_checked"]], ["Exact / within 3 runs", f"{rc['exact_pct']}% / {rc['within3_pct']}%"]]))
    para(au["extras_encoding_note"] + " Legal deliveries exclude wides, no-balls (Overstep) and 'other' (shown to be illegal: treating it as illegal increases the share of 6-legal-ball overs). "
         "Batter balls faced exclude wides only. Bowler runs exclude byes/leg-byes; bowler wickets exclude run-outs, retirements and obstruction.")
    sec(5, "Domestic Player Identification and Eligibility")
    s = el["summary"]
    para(f"Player universe: <b>{s['total_players']}</b> unique IDs across mapping, playing XIs and deliveries. Official PDF scope (IPL + T20I data, no uncapped restriction stated) treats all as eligible. "
         f"An additional <b>Uncapped Lens</b> flags <b>{s['capped_in_data_ineligible_lens']}</b> players as capped because they appear in a full T20 International in the data; "
         f"the remaining <b>{s['unverified_lens']}</b> are <b>Unverified</b> - absence of a T20I in 2022-26 does not prove uncapped status (Tests/ODIs/pre-2022 caps are not in the data).")
    para(f"Discrepancy noted: the live Unstop card mentions 'domestic leagues' while the official PDF describes IPL and T20I data. Homonyms resolved by ID: {', '.join(s['homonyms'])}.")
    sec(6, "Domestic Data Coverage and Limitations")
    para(f"Domestic competitions searched (SMAT, Vijay Hazare, Ranji, Duleep, Deodhar): found {au['domestic_competitions_found'] or 'none'}. "
         "No state-domestic statistics exist in the data pack and none were fabricated. Emerging Asia Cup / Rising Stars (A-team) matches are the closest proxy and are tagged 'Emerging'.")
    add(PageBreak())
    sec(7, "Pressure Definition Framework")
    para("For each delivery the pre-ball state s = (innings, runs, wickets, legal balls left, target, competition) is fed to two logistic win-probability (WP) models "
         "(setting and chasing). Leverage L(s) = WP(s after +4 runs) - WP(s after a wicket). The Leverage Index LI = L / mean(L). Because setting-innings WP is less certain, "
         f"tiers are assigned by quantiles within each innings: Normal (&lt; P{int(pr['cutoffs']['q_mod']*100)}), Moderate, High (&ge; P{int(pr['cutoffs']['q_high']*100)}). "
         "This hybrid keeps a continuous index and three interpretable tiers. Required-vs-current rate gap, wickets in hand, balls left, target difficulty and match closeness "
         "enter through the WP surface rather than arbitrary hand thresholds.")
    wv = pr["wp_validation"]
    add(tbl([["WP model", "Train", "Test", "Test deliveries", "AUC", "Brier"]] +
            [[k, wv["train_seasons"], wv["test_seasons"], f"{wv[k]['n_test_deliveries']:,}", wv[k]["auc"], wv[k]["brier"]] for k in ["innings_1", "innings_2"]]))
    add(Spacer(1, 4))
    add(tbl([["Tier", "Balls", "Share", "SR", "Out %", "Dot %", "Bdry %", "Mean LI", "% close-finish matches"]] +
            [[t["tier"], f"{t['balls']:,}", t["share"], t["strike_rate"], t["dismissal_pct"], t["dot_pct"], t["boundary_pct"], t["mean_LI"], pr["close_match_pct_by_tier"][t["tier"]]] for t in pr["tiers"]]))
    para("Validation of the definition: High-tier deliveries come disproportionately from matches with close final margins (&le;15 runs or &le;3 wickets), and the league strike rate falls under pressure - "
         "the tiers capture genuinely different contests, not just death overs.")
    add(chart(out / "c_li.png", lambda ax: (ax.bar([h["x"] for h in pr["li_hist"]], [h["n"] for h in pr["li_hist"]], width=0.18, color=PURPLE),
                                            ax.set_xlabel("Leverage Index", fontsize=7), ax.set_ylabel("Deliveries", fontsize=7))))
    sec(8, "Pressure Feature Engineering")
    para("Pre-delivery cumulative score, wickets and legal balls are computed with shifted cumulative sums inside each innings (no future information). Ball limits use revised overs where present; "
         "chase targets use revised targets else first-innings total + 1. Features: required rate (clipped 0-36), wickets in hand, balls left, log required runs, interactions, IPL flag. "
         "Wicket run value W(over, wickets) = drop in first-innings run expectancy when one more wicket falls (smoothed, 1-25 runs). Real example deliveries:")
    ex = pr["examples"][:10]
    add(tbl([["Match", "Date", "Over", "Score/Wk", "Req", "Balls left", "WP", "LI", "Tier"]] +
            [[e["match_id"], e["match_date"], f"{e['overid']}.{e['over_ball_num']}", f"{int(e['score'])}/{int(e['wk'])}", f(e["req"], 0), i_(e["balls_left"]), f(e["wp_before"], 2), f(e["LI"], 2), e["bat_tier"]] for e in ex]))
    sec(9, "Batting Pressure Methodology")
    para("Per ball faced: RV_bat = (runs - v*E[runs|ctx]) - W*(dismissed - P[out|ctx]), ctx = competition group x innings x phase x wickets-lost bucket x pressure tier, v = venue factor. "
         "This rewards scoring and survival jointly versus what an average batter does in the identical situation, so strike rate alone is not rewarded. Roles from median batting position "
         "(1-2 Opener, 3 Top, 4-5 Middle, 6-7 Finisher, 8+ Lower).")
    sec(10, "Bowling Pressure Methodology")
    para("Per delivery (incl. wides/no-balls): RV_bowl = (v*E[conceded|ctx] - conceded) + W*(bowler wicket - P[wicket|ctx]). Economy and wicket-taking share one run currency, "
         "so neither wickets nor economy is rewarded alone. Roles: >=50% of legal balls in one phase = specialist; >=20% in all phases = versatile; else multi-phase.")
    sec(11, "Venue and Ground Conditions Analysis")
    vm = ven["meta"]
    para(f"Venue names, pitch reports, weather, dew and boundary dimensions are NOT in the data pack and are not invented. Venue IDs are analysed by observed outcomes only. "
         f"Kruskal-Wallis test of first-innings totals across {vm['venues_tested']} venues (&ge;5 matches): H = {vm['kruskal_H']}, p = {vm['kruskal_p']} -> adjustment applied = {vm['adjustment_applied']}. "
         f"Venue factor = shrunk ratio of venue runs/ball to its competition-group mean (prior {int(vm['shrinkage_prior_balls'])} balls). RR home venues inferred from fixture patterns: IDs {ven['rr_home_venue_ids']}.")
    vv = ven["venues"][:14]
    add(tbl([["Venue ID", "Country", "M", "Avg 1st inn", "RR", "Chase win %", "Pace econ", "Spin econ", "Spin wkt %", "Factor", "IPL home (inferred)"]] +
            [[v["venue_id"], v["country"], v["matches"], f(v["avg_first_innings"]), v["run_rate"], f(v["chasing_win_pct"]), v["pace_econ"], v["spin_econ"], v["spin_wkt_share"], v["venue_factor"], (v["ipl_home_team_inferred"] or "-")[:22]] for v in vv], font=6.2))
    add(PageBreak())
    sec(12, "Mathematical Scoring Framework")
    para("Components per player (pressure = Moderate + High tiers): "
         "<b>Q</b> Pressure quality = sum(RV_press)/(n_press + k)*100 (empirical-Bayes shrinkage to league mean 0); "
         "<b>D</b> Rise vs baseline = Q - sum(RV_normal)/(n_normal + k_n)*100; "
         "<b>C</b> Consistency = (successful pressure innings + 10*league rate)/(pressure innings + 10), success = innings pressure RV &ge; 0, innings with &ge;6 pressure balls. "
         "Rating = 50 + 10*(0.50*z(Q) + 0.25*z(D) + 0.25*z(C)), z among qualified players. Q carries half the weight because the brief asks who performs best <i>under pressure</i>; "
         "D answers 'compared with usual' and C answers 'consistently'. Weights are stress-tested in section 19.")
    add(tbl([["Parameter", "Batting", "Bowling"], ["k (shrinkage, pressure) = sigma^2/tau^2", bm["k_pressure"], wm["k_pressure"]], ["k (normal)", bm["k_normal"], wm["k_normal"]],
             ["Per-ball RV variance sigma^2", bm["sigma2"], wm["sigma2"]], ["Between-player variance tau^2", bm["tau2"], wm["tau2"]],
             ["League pressure-innings success", bm["league_innings_success"], wm["league_innings_success"]],
             ["Corr(Q,C)", bat["component_corr"]["quality"]["consistency"], bowl["component_corr"]["quality"]["consistency"]],
             ["Corr(Q,D)", bat["component_corr"]["quality"]["delta"], bowl["component_corr"]["quality"]["delta"]]]))
    sec(13, "Player Eligibility and Sample Rules")
    para(f"Minimum pressure sample where reliability n/(n+k) &ge; 0.20: batting &ge; <b>{bm['n_min_pressure_balls']}</b> pressure balls faced, bowling &ge; <b>{wm['n_min_pressure_balls']}</b> pressure deliveries; "
         f"plus &ge; {bm['min_pressure_innings']} pressure innings. Qualified: {bm['n_qualified']} batters, {wm['n_qualified']} bowlers. Shrinkage further discounts small samples, "
         "so a handful of pressure balls cannot outrank sustained performers.")

    def top_table(rows, disc):
        if disc == "bat":
            hdr = ["#", "Player", "Role", "Rating", "Normal R-B (SR)", "Pressure R-B (SR)", "P outs", "Q", "D", "C", "Boot %", "Cap"]
            body = [[i_(r["rank"]), r["name"], r["role"], f(r["rating"]), f"{i_(r['normal_runs'])}-{i_(r['normal_balls'])} ({f(r['normal_sr'])})",
                     f"{i_(r['pressure_runs'])}-{i_(r['pressure_balls'])} ({f(r['pressure_sr'])})", i_(r["pressure_outs"]), f(r["quality"]), f(r["delta"]), f(r["consistency"], 2),
                     f(r["boot_top10_pct"], 0), "T20I" if r["capped_in_data"] else "Unver."] for r in rows]
        else:
            hdr = ["#", "Player", "Role", "Rating", "Normal econ (W)", "Pressure econ (W)", "P balls", "Q", "D", "C", "Boot %", "Cap"]
            body = [[i_(r["rank"]), r["name"], r["role"].replace(" specialist", ""), f(r["rating"]), f"{f(r['normal_econ'], 2)} ({i_(r['normal_wkts'])})",
                     f"{f(r['pressure_econ'], 2)} ({i_(r['pressure_wkts'])})", i_(r["pressure_balls"]), f(r["quality"]), f(r["delta"]), f(r["consistency"], 2),
                     f(r["boot_top10_pct"], 0), "T20I" if r["capped_in_data"] else "Unver."] for r in rows]
        return tbl([hdr] + body, font=6.2)

    def bars(rows, col, xlabel):
        def fn(ax):
            names = [r["name"] for r in rows][::-1]
            ax.barh(names, [r["baseline"] for r in rows][::-1], color="#8A8FA3", label="Normal baseline")
            ax.barh(names, [r["quality"] for r in rows][::-1], color=col, alpha=0.85, height=0.45, label="Pressure (shrunk)")
            ax.set_xlabel(xlabel, fontsize=7)
            ax.legend(fontsize=6)
        return fn
    sec(14, "Top 10 Batters Under Pressure")
    add(top_table(tb, "bat"))
    add(chart(out / "c_bat.png", bars(tb, PURPLE, "Runs value per 100 balls above context"), h=7))
    sec(15, "Top 10 Bowlers Under Pressure")
    add(top_table(tw, "bowl"))
    add(chart(out / "c_bowl.png", bars(tw, GOLD, "Runs saved per 100 deliveries above context"), h=7))
    add(PageBreak())
    sec(16, "Individual Player Evidence")
    for disc, rows, store in [("bat", tb, bat), ("bowl", tw, bowl)]:
        for r in rows:
            pf = store["profiles"].get(str(r["player_id"]), {})
            add(Paragraph(f"#{i_(r['rank'])} {r['name']} - {'Batting' if disc == 'bat' else 'Bowling'} | {r['role']} | Rating {f(r['rating'])} | {', '.join(r['teams'] or [])[:80]}", H2))
            tiers = pf.get("tiers", {})
            if disc == "bat":
                tr = [["Tier", "Runs", "Balls", "Outs", "SR", "Avg", "Bdry %", "Dot %", "RV/100"]] + [[t, i_(v["runs"]), i_(v["balls"]), i_(v["outs"]), f(v["sr"]), f(v["avg"]), f(v["bdry_pct"]), f(v["dot_pct"]), f(v["rv100"])] for t, v in tiers.items()]
            else:
                tr = [["Tier", "Runs", "Legal balls", "Wkts", "Econ", "Avg", "SR", "Dot %", "RV/100"]] + [[t, i_(v["runs"]), i_(v["balls"]), i_(v["wkts"]), f(v["econ"], 2), f(v["avg"]), f(v["sr"]), f(v["dot_pct"]), f(v["rv100"])] for t, v in tiers.items()]
            add(tbl(tr, font=6.5))
            phs = "; ".join(f"{k.split('|')[0]}: {i_(v['balls'])}b RV/100 {f(v['rv100'])}" for k, v in pf.get("phases", {}).items() if k.endswith("Pressure"))
            nx = pf.get("next_ranked")
            para(f"Calculation: Q {f(r['quality'])}, D {f(r['delta'])}, C {f(r['consistency'], 3)} ({i_(r['p_succ'])}/{i_(r['p_inn'])} pressure innings successful), reliability {f(r['reliability'], 2)}, "
                 f"raw pressure RV/100 90% CI [{f(r['ci_low'])}, {f(r['ci_high'])}]. Bootstrap rank median {f(r['boot_median_rank'], 0)} (P5-P95 {f(r['boot_rank_p05'], 0)}-{f(r['boot_rank_p95'], 0)}); "
                 f"top-10 in {f(r['weight_top10_pct'], 0)}% of weight specifications; rating without best innings {f(r['rating_wo_best'])}. Pressure by phase - {phs}. "
                 + (f"Next ranked: {nx['name']} ({nx['rating']}; Q {nx['quality']}, D {nx['delta']}, C {nx['consistency']})." if nx else ""))
            ms = pf.get("matches", [])[:4]
            if ms:
                if disc == "bat":
                    mt = [["Match", "Date", "Comp", "Inn", "vs", "R-B", "Press b", "RV", "Entry state"]] + [[m["match_id"], m["date"], m["comp"][:26], m["innings"], str(m["opp"])[:18], f"{i_(m['runs'])}-{i_(m['balls'])}", i_(m["press_balls"]), f(m["rv"]),
                                                                                                         f"{i_(m['entry_score'])}/{i_(m['entry_wk'])}" + (f" chasing {i_(m['target'])}" if m["target"] else "")] for m in ms]
                else:
                    mt = [["Match", "Date", "Comp", "Inn", "vs", "Balls-R-W", "Press b", "RV", "State at first ball"]] + [[m["match_id"], m["date"], m["comp"][:26], m["innings"], str(m["opp"])[:18], f"{i_(m['balls'])}-{i_(m['runs'])}-{i_(m['wkts'])}", i_(m["press_balls"]), f(m["rv"]),
                                                                                                                 f"{i_(m['entry_score'])}/{i_(m['entry_wk'])}" + (f" target {i_(m['target'])}" if m["target"] else "")] for m in ms]
                add(tbl(mt, font=6))
            add(Spacer(1, 5))
        add(PageBreak())
    sec(17, "Phase-Wise Analysis")
    para("Phase-level pressure RV for every top-10 player is listed in section 16 and in the Batting/Bowling Analytics dashboards.")
    add(tbl([["Phase", "Normal balls", "Moderate balls", "High balls"]] + [[p["phase"], f"{p.get('Normal', 0):,}", f"{p.get('Moderate', 0):,}", f"{p.get('High', 0):,}"] for p in pr["phase_tier_counts"]]))
    sec(18, "Venue-Wise Analysis")
    para("Top-10 players' records at inferred RR home venues versus elsewhere are in the Venue Intelligence dashboard. Removing the venue adjustment changes the batting top-10 by "
         f"{10 - bat['venue_adjust_effect']['top10_overlap']} player(s) (Spearman {bat['venue_adjust_effect']['spearman']}) and bowling by {10 - bowl['venue_adjust_effect']['top10_overlap']} "
         f"(Spearman {bowl['venue_adjust_effect']['spearman']}) - the venue layer refines but does not override the pressure objective.")
    sec(19, "Consistency and Robustness Testing")
    for nm, st in [("Batting", bat), ("Bowling", bowl)]:
        add(Paragraph(nm, H2))
        add(tbl([["Tier quantiles (mod, high)", "Qualified", "Top-10 overlap", "Spearman"]] + [[f"{t['q_mod']}, {t['q_high']}", t["n_qualified"], t["top10_overlap"], t["spearman_common"]] for t in st["threshold_sensitivity"]]))
        add(Spacer(1, 3))
        add(tbl([["Sample scale", "Min pressure balls", "Qualified", "Top-10 overlap"]] + [[s_["scale"], s_["n_min"], s_["n_qualified"], s_["top10_overlap"]] for s_ in st["sample_sensitivity"]]))
        g = st["weight_grid"]
        para(f"Weight grid ({len(g)} specifications, w_Q 0.34-0.70): mean top-10 overlap {sum(x['top10_overlap'] for x in g) / len(g):.1f}/10, min Spearman {min(x['spearman_vs_base'] for x in g)}. "
             f"Temporal trait test (2022-24 vs 2025-26, {st['temporal']['players']} players with &ge;60 pressure balls in both): Pearson r = {st['temporal']['pearson_r']}.")
    sec(20, "Ranking Stability")
    for nm, rows, col in [("bat", tb, PURPLE), ("bowl", tw, GOLD)]:
        def fn(ax, rows=rows, col=col):
            ax.errorbar([r["boot_median_rank"] for r in rows], range(len(rows)),
                        xerr=[[r["boot_median_rank"] - r["boot_rank_p05"] for r in rows], [r["boot_rank_p95"] - r["boot_median_rank"] for r in rows]], fmt="o", color=col, ms=3, lw=1)
            ax.set_yticks(range(len(rows)))
            ax.set_yticklabels([r["name"] for r in rows], fontsize=6)
            ax.invert_yaxis()
            ax.set_xlabel("Bootstrap rank (median, P5-P95; 300 match resamples)", fontsize=7)
        add(chart(out / f"c_boot_{nm}.png", fn, h=6.5))
    para("Leading positions are the most stable; lower top-10 positions overlap substantially and should be read as a tier rather than a strict order. This uncertainty is reported, not hidden.")
    sec(21, "Requirement Coverage")
    add(tbl([["Area", "Requirement", "Status", "Evidence"]] + [[r["area"], Paragraph(r["requirement"], SM), r["status"], Paragraph(r["evidence"], SM)] for r in rq["items"]],
            [2.2 * cm, 7 * cm, 2 * cm, 6 * cm], 6.5))
    para(f"Official requirement completion: <b>{rq['official_completion']}%</b>.")
    sec(22, "Key Findings")
    para(f"(1) Pressure skill is real but noisy: between-player variance is small relative to ball-level noise (batting k = {bm['k_pressure']}, bowling k = {wm['k_pressure']}), so heavy shrinkage is essential. "
         f"(2) The league strike rate drops from {pr['tiers'][0]['strike_rate']} (normal) to {pr['tiers'][2]['strike_rate']} (high pressure); players who hold scoring and survival above context are rare. "
         f"(3) Era-to-era repeatability of pressure RV: batting r = {bat['temporal']['pearson_r']}, bowling r = {bowl['temporal']['pearson_r']}.")
    sec(23, "Limitations and Uncertainty")
    para("Bye/leg-bye/wide run values are not stored (team totals approximate; reconciliation reported). No venue names, pitch, weather, dew or boundary data. Uncapped status cannot be fully verified from the data; "
         "Unverified players require manual checks. Opposition strength is not modelled. First-innings WP is less discriminating (AUC reported), mitigated by innings-specific tiering.")
    sec(24, "Final Recruitment Insights")
    para("The most defensible targets are players ranked in the top 10 in &ge;50% of bootstrap resamples AND &ge;60% of weight specifications (flagged 'Robust' in the dashboard). "
         "Use the Uncapped Lens to shortlist auction-eligible names, then verify caps externally.")
    sec(25, "Technical Appendix and Reproducibility")
    para("Run: <i>cd backend && python -m analytics.run &lt;raw_dir&gt; outputs</i>. Modules: engine.py (ingestion, audit, state reconstruction, WP, pressure, venue, expectations), ratings.py (universe, ratings, shrinkage, bootstrap, sensitivity), "
         f"run.py (orchestration, versioning), report.py. File fingerprints: {ov['files']['fingerprints']}. Engineered deliveries exported as engineered_deliveries.csv.gz for independent verification.")
    SimpleDocTemplate(str(out / "methodology_report.pdf"), pagesize=A4, leftMargin=1.4 * cm, rightMargin=1.4 * cm, topMargin=1.3 * cm, bottomMargin=1.3 * cm,
                      title="RR SupeRR Selector - Pressure Intelligence Report").build(S)
