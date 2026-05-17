"""
visualizations.py
-----------------
Visualization module for Resume Job Matcher.
Generates matplotlib charts and exports them as PNG.
"""

import io
import base64
import matplotlib
matplotlib.use("Agg")          # non-interactive backend — safe for Flask
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


# ─── Shared helpers ───────────────────────────────────────────────────────────

PALETTE = ["#4F8EF7", "#F76B6B", "#6BF7A0", "#F7D46B", "#C46BF7",
           "#F79E6B", "#6BD4F7", "#F76BC4"]

def _fig_to_base64(fig) -> str:
    """Convert a matplotlib figure to a base64 PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.close(fig)
    return encoded


def fig_to_bytes(fig) -> bytes:
    """Return raw PNG bytes (used for direct file download)."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    data = buf.read()
    buf.close()
    plt.close(fig)
    return data


# ─── 1. Score Comparison Bar Chart ───────────────────────────────────────────

def score_comparison_chart(candidates: list, job_title: str = "Job") -> str:
    """
    Bar chart comparing match scores for all candidates.
    candidates: [{"name": "Alice", "score": 87.5}, ...]
    Returns base64 PNG string.
    """
    if not candidates:
        raise ValueError("No candidates provided.")

    names  = [c["name"]  for c in candidates]
    scores = [c["score"] for c in candidates]
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(names))]

    fig, ax = plt.subplots(figsize=(max(8, len(names) * 1.2), 5),
                           facecolor="#F9FAFB")
    ax.set_facecolor("#F9FAFB")

    bars = ax.bar(names, scores, color=colors, width=0.55,
                  edgecolor="white", linewidth=1.2, zorder=3)

    for bar, score in zip(bars, scores):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1.2,
                f"{score:.1f}%",
                ha="center", va="bottom",
                fontsize=10, fontweight="bold", color="#1F2937")

    ax.set_ylim(0, 110)
    ax.set_xlabel("Candidates", fontsize=11, color="#374151")
    ax.set_ylabel("Match Score (%)", fontsize=11, color="#374151")
    ax.set_title(f"Candidate Score Comparison — {job_title}",
                 fontsize=14, fontweight="bold", color="#111827", pad=14)
    ax.tick_params(colors="#6B7280")
    ax.axhline(y=70, color="#EF4444", linestyle="--", linewidth=1,
               label="Min. threshold (70%)", zorder=2)
    ax.legend(fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    return _fig_to_base64(fig)


# ─── 2. Candidate Ranking Horizontal Bar ─────────────────────────────────────

def candidate_ranking_chart(candidates: list, top_n: int = 10) -> str:
    """
    Horizontal ranked bar chart (best candidate at top).
    candidates: [{"name": "Alice", "score": 87.5}, ...]
    Returns base64 PNG string.
    """
    if not candidates:
        raise ValueError("No candidates provided.")

    ranked = sorted(candidates, key=lambda c: c["score"])[-top_n:]
    names  = [c["name"]  for c in ranked]
    scores = [c["score"] for c in ranked]

    norm_scores = [(s - min(scores)) / (max(scores) - min(scores) + 1e-9)
                   for s in scores]
    colors = plt.cm.RdYlGn(norm_scores)

    fig, ax = plt.subplots(figsize=(9, max(4, len(names) * 0.55)),
                           facecolor="#F9FAFB")
    ax.set_facecolor("#F9FAFB")

    bars = ax.barh(names, scores, color=colors, height=0.6,
                   edgecolor="white", linewidth=0.8, zorder=3)

    for bar, score in zip(bars, scores):
        ax.text(bar.get_width() + 0.8, bar.get_y() + bar.get_height() / 2,
                f"{score:.1f}%",
                va="center", fontsize=9, fontweight="bold", color="#1F2937")

    ax.set_xlim(0, 115)
    ax.set_xlabel("Match Score (%)", fontsize=11, color="#374151")
    ax.set_title(f"Candidate Ranking (Top {len(ranked)})",
                 fontsize=14, fontweight="bold", color="#111827", pad=14)
    ax.tick_params(colors="#6B7280")
    ax.axvline(x=70, color="#EF4444", linestyle="--",
               linewidth=1, label="Min. threshold (70%)", zorder=2)
    ax.legend(fontsize=9)
    ax.grid(axis="x", linestyle="--", alpha=0.4, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    return _fig_to_base64(fig)


# ─── 3. Skill Match Radar Chart ───────────────────────────────────────────────

def skill_radar_chart(candidate_name: str, skill_scores: dict) -> str:
    """
    Radar / spider chart for one candidate's skill breakdown.
    skill_scores: {"Python": 90, "SQL": 75, "ML": 60, ...}
    Returns base64 PNG string.
    """
    categories = list(skill_scores.keys())
    values     = list(skill_scores.values())
    N = len(categories)
    if N < 3:
        raise ValueError("Radar chart needs at least 3 skills.")

    angles       = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    values_loop  = values + [values[0]]
    angles_loop  = angles + [angles[0]]

    fig, ax = plt.subplots(figsize=(6, 6),
                           subplot_kw={"projection": "polar"},
                           facecolor="#F9FAFB")
    ax.set_facecolor("#EFF6FF")

    ax.plot(angles_loop, values_loop, color="#4F8EF7", linewidth=2)
    ax.fill(angles_loop, values_loop, color="#4F8EF7", alpha=0.25)

    ax.set_xticks(angles)
    ax.set_xticklabels(categories, fontsize=10, color="#1F2937")
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"],
                       fontsize=7, color="#9CA3AF")
    ax.grid(color="#CBD5E1", linestyle="--", linewidth=0.6)
    ax.set_title(f"Skill Match Radar — {candidate_name}",
                 fontsize=13, fontweight="bold", color="#111827", pad=18)

    plt.tight_layout()
    return _fig_to_base64(fig)


# ─── 4. Score Distribution Histogram ─────────────────────────────────────────

def score_distribution_chart(candidates: list) -> str:
    """
    Histogram of all match scores.
    candidates: [{"name": "Alice", "score": 87.5}, ...]
    Returns base64 PNG string.
    """
    scores = [c["score"] for c in candidates]

    fig, ax = plt.subplots(figsize=(8, 4.5), facecolor="#F9FAFB")
    ax.set_facecolor("#F9FAFB")

    n, bins, patches = ax.hist(scores, bins=10, range=(0, 100),
                               edgecolor="white", linewidth=0.8, zorder=3)

    for patch, left in zip(patches, bins[:-1]):
        if left < 50:
            patch.set_facecolor("#F76B6B")
        elif left < 70:
            patch.set_facecolor("#F7D46B")
        else:
            patch.set_facecolor("#6BF7A0")

    red_p    = mpatches.Patch(color="#F76B6B", label="<50%  Poor")
    yellow_p = mpatches.Patch(color="#F7D46B", label="50–70%  Fair")
    green_p  = mpatches.Patch(color="#6BF7A0", label=">70%  Good")
    ax.legend(handles=[red_p, yellow_p, green_p], fontsize=9)

    ax.set_xlabel("Match Score (%)", fontsize=11, color="#374151")
    ax.set_ylabel("Number of Candidates", fontsize=11, color="#374151")
    ax.set_title("Score Distribution",
                 fontsize=14, fontweight="bold", color="#111827", pad=14)
    ax.tick_params(colors="#6B7280")
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    return _fig_to_base64(fig)


# ─── 5. Export helpers (raw bytes for download) ──────────────────────────────

def export_chart_png(chart_type: str,
                     candidates: list,
                     job_title: str = "Job",
                     candidate_name: str = "",
                     skill_scores: dict = None) -> bytes:
    """
    Returns raw PNG bytes for direct HTTP download.
    chart_type: "comparison" | "ranking" | "distribution" | "radar"
    """
    builders = {
        "comparison":  lambda: _build_fig_comparison(candidates, job_title),
        "ranking":     lambda: _build_fig_ranking(candidates),
        "distribution":lambda: _build_fig_distribution(candidates),
        "radar":       lambda: _build_fig_radar(candidate_name, skill_scores or {}),
    }
    if chart_type not in builders:
        raise ValueError(f"Unknown chart_type: {chart_type}")
    return fig_to_bytes(builders[chart_type]())


# ── private figure builders (return unclosed fig for export) ─────────────────

def _build_fig_comparison(candidates, job_title):
    names  = [c["name"]  for c in candidates]
    scores = [c["score"] for c in candidates]
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(names))]
    fig, ax = plt.subplots(figsize=(max(8, len(names) * 1.2), 5),
                           facecolor="#F9FAFB")
    ax.set_facecolor("#F9FAFB")
    bars = ax.bar(names, scores, color=colors, width=0.55,
                  edgecolor="white", linewidth=1.2, zorder=3)
    for bar, score in zip(bars, scores):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1.2, f"{score:.1f}%",
                ha="center", va="bottom", fontsize=10,
                fontweight="bold", color="#1F2937")
    ax.set_ylim(0, 110)
    ax.axhline(y=70, color="#EF4444", linestyle="--", linewidth=1)
    ax.set_title(f"Candidate Score Comparison — {job_title}",
                 fontsize=14, fontweight="bold", pad=14)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    return fig


def _build_fig_ranking(candidates, top_n=10):
    ranked = sorted(candidates, key=lambda c: c["score"])[-top_n:]
    names  = [c["name"]  for c in ranked]
    scores = [c["score"] for c in ranked]
    norm   = [(s - min(scores)) / (max(scores) - min(scores) + 1e-9)
              for s in scores]
    colors = plt.cm.RdYlGn(norm)
    fig, ax = plt.subplots(figsize=(9, max(4, len(names) * 0.55)),
                           facecolor="#F9FAFB")
    ax.set_facecolor("#F9FAFB")
    ax.barh(names, scores, color=colors, height=0.6,
            edgecolor="white", linewidth=0.8, zorder=3)
    ax.set_xlim(0, 115)
    ax.axvline(x=70, color="#EF4444", linestyle="--", linewidth=1)
    ax.set_title(f"Candidate Ranking (Top {len(ranked)})",
                 fontsize=14, fontweight="bold", pad=14)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    return fig


def _build_fig_distribution(candidates):
    scores = [c["score"] for c in candidates]
    fig, ax = plt.subplots(figsize=(8, 4.5), facecolor="#F9FAFB")
    ax.set_facecolor("#F9FAFB")
    n, bins, patches = ax.hist(scores, bins=10, range=(0, 100),
                               edgecolor="white", linewidth=0.8, zorder=3)
    for patch, left in zip(patches, bins[:-1]):
        patch.set_facecolor(
            "#F76B6B" if left < 50 else "#F7D46B" if left < 70 else "#6BF7A0")
    ax.set_title("Score Distribution", fontsize=14, fontweight="bold", pad=14)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    return fig


def _build_fig_radar(candidate_name, skill_scores):
    categories  = list(skill_scores.keys())
    values      = list(skill_scores.values())
    N = len(categories)
    if N < 3:
        raise ValueError("Radar chart needs at least 3 skills.")
    angles      = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    values_loop = values + [values[0]]
    angles_loop = angles + [angles[0]]
    fig, ax = plt.subplots(figsize=(6, 6),
                           subplot_kw={"projection": "polar"},
                           facecolor="#F9FAFB")
    ax.set_facecolor("#EFF6FF")
    ax.plot(angles_loop, values_loop, color="#4F8EF7", linewidth=2)
    ax.fill(angles_loop, values_loop, color="#4F8EF7", alpha=0.25)
    ax.set_xticks(angles)
    ax.set_xticklabels(categories, fontsize=10)
    ax.set_ylim(0, 100)
    ax.set_title(f"Skill Radar — {candidate_name}",
                 fontsize=13, fontweight="bold", pad=18)
    plt.tight_layout()
    return fig
