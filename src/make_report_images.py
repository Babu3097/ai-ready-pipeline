"""
make_report_images.py - Phase 7 (preview version): draws the four report pages as PNG images.

WHY: Power BI Desktop only runs on Windows, and this was built on a Mac, so no .pbix file could be made here.
These images show exactly what the Power BI report should contain (see powerbi/BUILD_GUIDE.md), built from the
same CSV files Power BI will read (powerbi/data/). They are NOT Power BI screenshots.

Run:  python src/make_report_images.py     (after evaluate.py)
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import db

DATA = db.ROOT / "powerbi" / "data"
OUT = db.ROOT / "docs" / "screenshots" / "python_preview"
BLUE, ORANGE, GREY, RED, GREEN, INK = "#2F5D8C", "#D9822B", "#8A94A0", "#B23A3A", "#3C8D5A", "#1F2933"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": GREY, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK})


def page(title, subtitle, banner=None):
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor="white")
    fig.text(0.04, 0.94, title, fontsize=22, fontweight="bold", color=INK)
    fig.text(0.04, 0.895, subtitle, fontsize=11, color=GREY)
    if banner:
        fig.text(0.96, 0.94, banner, fontsize=10, color="white", ha="right", va="center",
                 bbox=dict(boxstyle="round,pad=0.4", fc=ORANGE, ec="none"))
    return fig


def tile(fig, x, y, value, label, color=BLUE, w=0.2):
    fig.text(x, y, value, fontsize=30, fontweight="bold", color=color)
    fig.text(x, y - 0.045, label, fontsize=10.5, color=GREY)


def label_bars(ax, fmt="{:.0f}", suffix=""):
    for p in ax.patches:
        if p.get_height() > 0:
            ax.annotate(fmt.format(p.get_height()) + suffix, (p.get_x() + p.get_width() / 2, p.get_height()),
                        ha="center", va="bottom", fontsize=9, color=INK, xytext=(0, 2), textcoords="offset points")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    f = pd.read_csv(DATA / "triage_facts.csv")
    ev = pd.read_csv(DATA / "eval_summary.csv").set_index("metric")["value"]
    q = pd.read_csv(DATA / "quality_scores.csv")
    sens = pd.read_csv(DATA / "value_sensitivity.csv")
    modes = set(f["ai_mode"].dropna())
    demo = modes == {"demo"}
    banner = ("DEMO MODE: keyword stand-in, not Claude" if demo else
              "Claude Code chat session, not the API; not independent" if modes == {"claude-code-session"} else None)
    sub = "Northfield Services (fictional) - all data is synthetic"
    orig = f[f["row_type"] == "original"]

    # ---------- page 1: overview ----------
    fig = page("1. Overview", sub)
    open_urgent = int(((f["status"] == "Open") & (f["urgency_final"] == "High")).sum())
    tile(fig, 0.04, 0.80, f"{len(f)}", "enquiries in the quarter")
    tile(fig, 0.27, 0.80, f"{ev['Review rate']:.0f}%", "need a person to decide", ORANGE)
    tile(fig, 0.50, 0.80, f"{open_urgent}", "urgent cases still open", RED)
    tile(fig, 0.73, 0.80, f"{f['handling_mins'].mean():.1f} min", "average handling time (closed)")
    ax = fig.add_axes([0.16, 0.10, 0.31, 0.55])
    c = f["category_final"].fillna("Unknown").value_counts()
    ax.barh(c.index[::-1], c.values[::-1], color=BLUE)
    ax.set_title("Enquiries by category", loc="left", fontsize=13, color=INK)
    for i, v in enumerate(c.values[::-1]):
        ax.text(v + 0.5, i, str(v), va="center", fontsize=9)
    ax2 = fig.add_axes([0.58, 0.10, 0.38, 0.55])
    m = f.dropna(subset=["month", "channel"]).groupby(["month", "channel"]).size().unstack(fill_value=0)
    m.plot(kind="bar", stacked=True, ax=ax2, color=[BLUE, ORANGE], width=0.6)
    ax2.set_title("Enquiries per month, by channel", loc="left", fontsize=13, color=INK)
    ax2.set_xlabel(""); ax2.tick_params(axis="x", rotation=0); ax2.legend(frameon=False)
    fig.savefig(OUT / "1_overview.png"); plt.close(fig)

    # ---------- page 2: data quality ----------
    fig = page("2. Data quality: before and after clean-up", sub)
    ax = fig.add_axes([0.07, 0.12, 0.55, 0.65])
    x = range(len(q))
    ax.bar([i - 0.2 for i in x], q["before"] * 100, 0.4, color=GREY, label="Before")
    ax.bar([i + 0.2 for i in x], q["after"] * 100, 0.4, color=BLUE, label="After")
    ax.set_xticks(list(x)); ax.set_xticklabels(q["metric"]); ax.set_ylim(0, 112); ax.set_ylabel("% of cells / rows")
    label_bars(ax, "{:.0f}", "%"); ax.legend(frameon=False, loc="upper left", ncol=2)
    fig.text(0.68, 0.72, "What changed", fontsize=14, fontweight="bold", color=INK)
    notes = [f"{(f['quality_status'] == 'fixed').sum()} rows fixed by rules",
             f"{(f['quality_status'] == 'needs_review').sum()} rows flagged for a person",
             f"{f['possible_duplicate_of'].notna().sum()} near-duplicates flagged, not deleted",
             "10 exact duplicates and 8 blank rows removed", "",
             "Completeness only reaches ~90%:", "a value we can't trust is blanked,", "never guessed."]
    for i, t in enumerate(notes):
        fig.text(0.68, 0.66 - i * 0.05, t, fontsize=11, color=INK)
    fig.savefig(OUT / "2_data_quality.png"); plt.close(fig)

    # ---------- page 3: AI performance ----------
    fig = page("3. AI performance", sub, banner)
    tile(fig, 0.04, 0.80, f"{ev['Category accuracy']:.0f}%", "category accuracy")
    tile(fig, 0.27, 0.80, f"{ev['Urgency accuracy']:.0f}%", "urgency accuracy")
    tile(fig, 0.50, 0.80, f"{ev['Review rate']:.0f}%", "sent to a person", ORANGE)
    missed = int(ev["Urgent missed AND not sent to a person"])
    tile(fig, 0.73, 0.80, f"{missed}", f"urgent cases missed silently (of {int(ev['Truly urgent enquiries'])})", GREEN if missed == 0 else RED)
    ax = fig.add_axes([0.07, 0.10, 0.36, 0.52])
    order = ["High", "Medium", "Low"]
    conf = pd.crosstab(orig["true_urgency"], orig["ai_urgency"].fillna("None")).reindex(index=order, columns=order + ["None"], fill_value=0)
    ax.imshow(conf.values, cmap="Blues")
    ax.set_xticks(range(4)); ax.set_xticklabels(conf.columns); ax.set_yticks(range(3)); ax.set_yticklabels(conf.index)
    ax.set_xlabel("AI said"); ax.set_ylabel("Truth"); ax.set_title("Urgency: truth vs AI", loc="left", fontsize=13)
    for i in range(3):
        for j in range(4):
            ax.text(j, i, conf.values[i, j], ha="center", va="center", color="white" if conf.values[i, j] > 60 else INK, fontsize=12)
    ax.spines[:].set_visible(False)
    ax2 = fig.add_axes([0.57, 0.10, 0.38, 0.52])
    both = (orig["category_correct"] == 1) & (orig["urgency_correct"] == 1)
    grp = orig.assign(right=both).groupby("needs_human_review")["right"].agg(["mean", "size"])
    labels = ["Skim only\n(not reviewed)", "Sent to a person"]
    ax2.bar(labels, [grp.loc[0, "mean"] * 100, grp.loc[1, "mean"] * 100], color=[GREEN, ORANGE], width=0.5)
    label_bars(ax2, "{:.0f}", "%"); ax2.set_ylim(0, 115); ax2.set_ylabel("% fully right")
    ax2.set_title("AI accuracy by route", loc="left", fontsize=13)
    for i, k in enumerate([0, 1]):
        ax2.text(i, 8, f"n={int(grp.loc[k, 'size'])}", ha="center", color="white", fontsize=10)
    fig.savefig(OUT / "3_ai_performance.png"); plt.close(fig)

    # ---------- page 4: value ----------
    fig = page("4. Value: hours and cost saved", sub, banner)
    tile(fig, 0.04, 0.80, f"{ev['Time saved']:.1f} h", f"saved on {int(ev['Enquiries scored'])} enquiries ({ev['Time saved %']:.0f}%)", GREEN)
    tile(fig, 0.30, 0.80, f"£{ev['Staff cost saved']:.0f}", "staff cost saved (assumed £18/h)", GREEN)
    tile(fig, 0.56, 0.80, f"£{ev['AI cost']:.2f}", "AI cost" + (" (no API billing)" if modes != {"claude"} else ""), BLUE)
    ax = fig.add_axes([0.07, 0.12, 0.30, 0.52])
    ax.bar(["Manual", "AI + human\nreview"], [ev["Manual triage time"], ev["Time with AI + human review"]], color=[GREY, BLUE], width=0.5)
    label_bars(ax, "{:.1f}", " h"); ax.set_ylabel("Triage hours"); ax.set_title("Triage time", loc="left", fontsize=13)
    ax2 = fig.add_axes([0.47, 0.12, 0.26, 0.52])
    ax2.plot(sens["review_minutes"].astype(str) + " min", sens["pct_saved"], marker="o", color=ORANGE, lw=2.5)
    ax2.set_ylim(0, 80); ax2.set_ylabel("% time saved"); ax2.set_title("If review takes longer...", loc="left", fontsize=13)
    for xv, yv in zip(sens["review_minutes"].astype(str) + " min", sens["pct_saved"]):
        ax2.text(xv, yv + 3, f"{yv:.0f}%", ha="center", fontsize=9)
    fig.text(0.78, 0.60, "Assumptions", fontsize=13, fontweight="bold", color=INK)
    for i, t in enumerate(["Manual triage: 4 min each", "AI skim: 0.5 min", "Review: 2 min", "Staff cost: £18/hour",
                           "Triage time only", "(not fixing the issue)"]):
        fig.text(0.78, 0.55 - i * 0.045, t, fontsize=10.5, color=INK)
    fig.savefig(OUT / "4_value.png"); plt.close(fig)
    print(f"Wrote 4 report pages to {OUT.relative_to(db.ROOT)}/")


if __name__ == "__main__":
    main()
