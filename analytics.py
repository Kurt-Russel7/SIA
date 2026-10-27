"""Analytics engine for SkyArch.

Loads the airline passenger satisfaction CSVs from ./data, keeps them cached in
memory (reloaded automatically when the active files change), and computes every
figure the dashboard shows.

Dataset columns used (Kaggle "Airline Passenger Satisfaction"):
  14 service ratings (0 = not applicable, 1–5 = rating), Customer Type, Age,
  Type of Travel, Class, Departure Delay in Minutes, satisfaction.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

import pandas as pd
from werkzeug.utils import secure_filename

from data import INITIATIVE_LIBRARY, SEGMENT_INFO

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
ACTIVE_FILE = DATA_DIR / "active.json"
DEFAULT_FILES = ["train.csv", "test.csv"]

DELAY_THRESHOLD = 15  # minutes of departure delay that count as "delayed"

# (dataset column, display label, journey area)
TOUCHPOINTS = [
    ("Inflight wifi service", "Inflight Wi-Fi", "Digital"),
    ("Departure/Arrival time convenient", "Departure/arrival time", "Operations"),
    ("Ease of Online booking", "Online booking", "Digital"),
    ("Gate location", "Gate location", "Ground"),
    ("Food and drink", "Food and drink", "Onboard"),
    ("Online boarding", "Online boarding", "Digital"),
    ("Seat comfort", "Seat comfort", "Onboard"),
    ("Inflight entertainment", "Inflight entertainment", "Onboard"),
    ("On-board service", "On-board service", "Onboard"),
    ("Leg room service", "Leg room", "Onboard"),
    ("Baggage handling", "Baggage handling", "Ground"),
    ("Checkin service", "Check-in service", "Ground"),
    ("Inflight service", "Inflight service", "Onboard"),
    ("Cleanliness", "Cleanliness", "Onboard"),
]
RATING_COLUMNS = [t[0] for t in TOUCHPOINTS]
REQUIRED_COLUMNS = RATING_COLUMNS + [
    "Customer Type", "Age", "Type of Travel", "Class", "Departure Delay in Minutes", "satisfaction",
]
SATISFACTION_VALUES = {"satisfied", "neutral or dissatisfied"}

CLASS_FILTERS = ["All classes", "Business", "Eco Plus", "Eco"]
SERVICE_FILTERS = ["All passengers", "Business travel", "Personal travel", "Delayed flights"]
AGE_BINS = [0, 19, 29, 39, 49, 59, 69, 200]
AGE_LABELS = ["<20", "20–29", "30–39", "40–49", "50–59", "60–69", "70+"]

_lock = threading.Lock()
_state: dict = {"key": None}


# ===================================================================== loading
def _active_names() -> list[str]:
    try:
        names = json.loads(ACTIVE_FILE.read_text())["files"]
    except (FileNotFoundError, ValueError, KeyError, TypeError):
        names = DEFAULT_FILES
    names = [n for n in names if (DATA_DIR / n).is_file()]
    return names or DEFAULT_FILES


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop(columns=[c for c in df.columns if str(c).startswith("Unnamed")])
    df["is_satisfied"] = df["satisfaction"].astype(str).str.strip().str.lower().eq("satisfied")
    df["is_delayed"] = df["Departure Delay in Minutes"].fillna(0) >= DELAY_THRESHOLD
    df["is_loyal"] = df["Customer Type"].astype(str).str.lower().eq("loyal customer")
    return df


def dataset() -> dict:
    """Return the cached dataset state, reloading if the active files changed."""
    names = _active_names()
    key = tuple((n, (DATA_DIR / n).stat().st_mtime) for n in names)
    with _lock:
        if _state["key"] != key:
            raw = pd.concat([pd.read_csv(DATA_DIR / n) for n in names], ignore_index=True)
            raw_columns = [c for c in raw.columns if not str(c).startswith("Unnamed")]
            _state.clear()
            _state.update(
                key=key,
                df=_prepare(raw),
                raw_columns=raw_columns,
                files=[Path(n).name for n in names],
                loaded_at=datetime.now(),
                memo={},
            )
        return _state


def _memo(name: str, arg, fn):
    """Cache a computed result for the current dataset version."""
    state = dataset()
    k = (name, arg)
    if k not in state["memo"]:
        state["memo"][k] = fn(state["df"])
    return state["memo"][k]


# ===================================================================== uploads
def validate_upload(file_storage) -> tuple[pd.DataFrame | None, str | None]:
    """Parse an uploaded CSV and check it matches the passenger dataset schema."""
    try:
        df = pd.read_csv(file_storage.stream)
    except Exception as exc:  # pandas raises several parser error types
        return None, f"Could not read that CSV ({exc.__class__.__name__})."
    if df.empty:
        return None, "That CSV file has no rows."
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        shown = ", ".join(missing[:4]) + (f" and {len(missing) - 4} more" if len(missing) > 4 else "")
        return None, f"Missing required columns: {shown}."
    bad = set(df["satisfaction"].astype(str).str.strip().str.lower()) - SATISFACTION_VALUES
    if bad:
        return None, "The satisfaction column must only contain 'satisfied' or 'neutral or dissatisfied'."
    ratings = df[RATING_COLUMNS]
    if not ratings.apply(pd.to_numeric, errors="coerce").isin(range(6)).all().all():
        return None, "Service ratings must be whole numbers from 0 to 5."
    return df, None


def save_upload(df: pd.DataFrame, filename: str, mode: str) -> str:
    """Store an uploaded dataset and make it active (replace or append)."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"uploads/{stamp}-{secure_filename(filename) or 'dataset.csv'}"
    df.to_csv(DATA_DIR / name, index=False)
    names = [name] if mode == "replace" else _active_names() + [name]
    ACTIVE_FILE.write_text(json.dumps({"files": names}, indent=2))
    return name


def reset_dataset() -> None:
    ACTIVE_FILE.unlink(missing_ok=True)


# ===================================================================== helpers
def _rate(series: pd.Series) -> float | None:
    return float(series.mean()) * 100 if len(series) else None


def _avg_rating(df: pd.DataFrame) -> float | None:
    vals = df[RATING_COLUMNS].where(df[RATING_COLUMNS] > 0)
    m = vals.stack().mean()
    return None if pd.isna(m) else float(m)


def fmt_pct(value: float | None, digits: int = 1) -> str:
    return "—" if value is None else f"{value:.{digits}f}%"


def fmt_pts(value: float | None) -> str:
    return "—" if value is None else f"{value:+.1f} pts"


def _status(mean: float | None) -> str:
    if mean is None:
        return "No data"
    if mean >= 3.5:
        return "Strong"
    if mean >= 3.2:
        return "Stable"
    if mean >= 3.0:
        return "Watch"
    return "At risk"


def touchpoint_stats(df: pd.DataFrame) -> list[dict]:
    """Per-touchpoint rating and its relationship with overall satisfaction.

    gap_pts      satisfaction rate of passengers rating it 4–5 minus those rating it 1–2
    opportunity  share of passengers rating it 1–2 × gap_pts — the most overall
                 satisfaction could rise if those passengers became as satisfied
                 as the 4–5 raters (an upper-bound estimate)
    ratio        how many times more likely 1–2 raters are to be neutral/dissatisfied
    """
    out = []
    n = len(df)
    for col, label, area in TOUCHPOINTS:
        s = df[col]
        rated = s[s > 0]
        low = df[(s >= 1) & (s <= 2)]
        high = df[s >= 4]
        mean = float(rated.mean()) if len(rated) else None
        sat_low, sat_high = _rate(low["is_satisfied"]), _rate(high["is_satisfied"])
        gap = sat_high - sat_low if sat_low is not None and sat_high is not None else None
        ratio = None
        if sat_low is not None and sat_high is not None and sat_high < 100:
            ratio = (100 - sat_low) / (100 - sat_high)
        out.append({
            "column": col, "label": label, "area": area,
            "mean": mean,
            "share_high": len(high) / len(rated) * 100 if len(rated) else None,
            "n_low": len(low),
            "gap_pts": gap,
            "opportunity": (len(low) / n * gap) if n and gap is not None else None,
            "ratio": ratio,
            "status": _status(mean),
        })
    return out


# ================================================================== filters
def _class_filter(df, cls):
    return df if cls == "All classes" else df[df["Class"] == cls]


def _service_filter(df, name):
    if name == "Business travel":
        return df[df["Type of Travel"] == "Business travel"]
    if name == "Personal travel":
        return df[df["Type of Travel"] == "Personal Travel"]
    if name == "Delayed flights":
        return df[df["is_delayed"]]
    return df


SEGMENT_MASKS = {
    "Business travelers": lambda d: d["Type of Travel"] == "Business travel",
    "Personal travelers": lambda d: d["Type of Travel"] == "Personal Travel",
    "Loyal customers": lambda d: d["is_loyal"],
    "Delay-affected": lambda d: d["is_delayed"],
}


# ============================================================ page builders
def meta() -> dict:
    """Small dataset summary used by the layout on every page."""
    def build(df):
        worst = min((t for t in touchpoint_stats(df) if t["mean"] is not None), key=lambda t: t["mean"])
        return {"rows": len(df), "worst": worst}
    state = dataset()
    m = _memo("meta", None, build)
    return {**m, "files": state["files"], "loaded_at": state["loaded_at"]}


def overview(cls: str) -> dict:
    def build(all_df):
        df = _class_filter(all_df, cls)
        filtered = cls != "All classes"
        sat, sat_all = _rate(df["is_satisfied"]), _rate(all_df["is_satisfied"])
        avg, avg_all = _avg_rating(df), _avg_rating(all_df)
        dly, dly_all = _rate(df["is_delayed"]), _rate(all_df["is_delayed"])

        def delta(v, base, lower_is_better=False):
            """Percentage-point difference from all classes (only when a class is selected)."""
            if not filtered or v is None or base is None:
                return None, True
            d = v - base
            return f"{d:+.1f} pts", (d <= 0) if lower_is_better else (d >= 0)

        sat_t, sat_pos = delta(sat, sat_all)
        avg_t, avg_pos = (None, True) if not filtered or avg is None else (f"{avg - avg_all:+.2f}", avg >= avg_all)
        dly_t, dly_pos = delta(dly, dly_all, lower_is_better=True)
        vs = "vs. all classes"

        metrics = [
            {"title": "Overall satisfaction", "value": fmt_pct(sat), "trend": sat_t, "positive": sat_pos,
             "accent": "sky", "note": vs if filtered else f"{int(df['is_satisfied'].sum()):,} satisfied passengers"},
            {"title": "Passengers analyzed", "value": f"{len(df):,}", "trend": None, "positive": True,
             "accent": "violet",
             "note": f"{len(df) / len(all_df) * 100:.1f}% of all records" if filtered else "All survey responses"},
            {"title": "Avg. service rating", "value": "—" if avg is None else f"{avg:.2f} / 5", "trend": avg_t,
             "positive": avg_pos, "accent": "amber", "note": vs if filtered else f"Across {len(TOUCHPOINTS)} touchpoints"},
            {"title": "Delayed flights", "value": fmt_pct(dly), "trend": dly_t, "positive": dly_pos,
             "accent": "rose", "note": vs if filtered else f"Departure delay of {DELAY_THRESHOLD}+ min"},
        ]

        # Satisfaction by age group, split by travel type
        groups = pd.cut(df["Age"], AGE_BINS, labels=AGE_LABELS)
        series = {}
        for name, value in [("Business", "Business travel"), ("Personal", "Personal Travel")]:
            sub = df[df["Type of Travel"] == value]
            rates = sub.groupby(groups[sub.index], observed=False)["is_satisfied"].agg(["mean", "size"])
            series[name] = [None if r["size"] < 20 else r["mean"] * 100 for _, r in rates.iterrows()]

        n_sat = int(df["is_satisfied"].sum())
        split = [
            {"label": "Satisfied", "count": n_sat, "pct": n_sat / len(df) * 100 if len(df) else 0,
             "color": "#0ea5e9", "dot": "sky"},
            {"label": "Neutral or dissatisfied", "count": len(df) - n_sat,
             "pct": (len(df) - n_sat) / len(df) * 100 if len(df) else 0, "color": "#fb7185", "dot": "rose-light"},
        ]

        tps = [t for t in touchpoint_stats(df) if t["mean"] is not None]
        ranked = sorted(tps, key=lambda t: t["mean"], reverse=True)
        bars = ranked[:3] + ranked[-3:] if len(ranked) > 6 else ranked
        colors = ["sky", "indigo", "violet", "amber", "orange", "rose"]
        bars = [{**t, "color": colors[i % len(colors)]} for i, t in enumerate(bars)]

        top = max((t for t in tps if t["opportunity"] is not None), key=lambda t: t["opportunity"], default=None)
        return {"metrics": metrics, "age_labels": AGE_LABELS, "age_series": series,
                "split": split, "bars": bars, "insight": top,
                "initiative": INITIATIVE_LIBRARY.get(top["column"]) if top else None}
    return _memo("overview", cls, build)


def data_workspace() -> dict:
    def build(df):
        state = dataset()
        raw_cols = state["raw_columns"]
        variables = [c for c in raw_cols if c not in ("id", "satisfaction")]
        complete = df[raw_cols].notna().all(axis=1).mean() * 100
        missing_rows = 100 - complete
        return {
            "pipeline": [
                ("Raw passenger data", f"{len(df):,} rows · {len(state['files'])} file(s)", "Complete"),
                ("Quality validation", f"{complete:.1f}% complete rows", "Complete" if complete >= 95 else "Watch"),
                ("Feature preparation", f"{len(variables)} variables · {len(TOUCHPOINTS)} service ratings", "Complete"),
                ("Analytics model", f"Computed {state['loaded_at']:%b %d, %H:%M}", "Live"),
            ],
            "stats": [(str(len(variables)), "Variables"), (f"{missing_rows:.1f}%", "Rows w/ missing"),
                      (str(len(TOUCHPOINTS)), "Service ratings")],
            "files": state["files"],
            "is_default": state["files"] == DEFAULT_FILES,
        }
    return _memo("data", None, build)


def services(name: str) -> dict:
    def build(all_df):
        df = _service_filter(all_df, name)
        tps = [t for t in touchpoint_stats(df) if t["mean"] is not None]
        strongest = max((t for t in tps if t["gap_pts"] is not None), key=lambda t: t["gap_pts"], default=None)
        weakest = min(tps, key=lambda t: t["mean"], default=None)
        on_time = _rate(df.loc[~df["is_delayed"], "is_satisfied"])
        delayed = _rate(df.loc[df["is_delayed"], "is_satisfied"])
        metrics = [
            {"title": "Strongest driver", "value": strongest["label"] if strongest else "—", "trend": None,
             "positive": True, "accent": "sky",
             "note": f"{fmt_pts(strongest['gap_pts'])} satisfaction when rated 4–5" if strongest else ""},
            {"title": "Largest service gap", "value": weakest["label"] if weakest else "—",
             "trend": f"{weakest['mean']:.2f} / 5" if weakest else None, "positive": False, "accent": "rose",
             "note": f"{weakest['n_low']:,} passengers rated it 1–2" if weakest else ""},
            {"title": "On-time satisfaction", "value": fmt_pct(on_time),
             "trend": fmt_pts(on_time - delayed) if on_time is not None and delayed is not None else None,
             "positive": on_time is not None and delayed is not None and on_time >= delayed, "accent": "violet",
             "note": "Compared with delayed flights" if on_time is not None else "No on-time flights in this filter"},
        ]
        rows = sorted(tps, key=lambda t: t["mean"], reverse=True)
        return {"metrics": metrics, "rows": rows, "count": len(df)}
    return _memo("services", name, build)


def segments(selected: str) -> dict:
    def build(df):
        cards = []
        for name, mask in SEGMENT_MASKS.items():
            sub = df[mask(df)]
            cards.append({"name": name, "count": len(sub), "satisfaction": _rate(sub["is_satisfied"]),
                          **SEGMENT_INFO[name]})
        sub = df[SEGMENT_MASKS[selected](df)]
        drivers = sorted((t for t in touchpoint_stats(sub) if t["gap_pts"] is not None),
                         key=lambda t: t["gap_pts"], reverse=True)[:4]
        current = next(c for c in cards if c["name"] == selected)
        return {
            "cards": cards,
            "current": {**current, "avg_rating": _avg_rating(sub), "loyalty": _rate(sub["is_loyal"])},
            "drivers": drivers,
        }
    return _memo("segments", selected, build)


def roadmap_items() -> list[dict]:
    """Top improvement opportunities turned into initiatives."""
    def build(df):
        tps = sorted((t for t in touchpoint_stats(df) if t["opportunity"] and t["opportunity"] > 0),
                     key=lambda t: t["opportunity"], reverse=True)[:4]
        quarters = ["Q4 2026", "Q1 2027", "Q2 2027", "Q3 2027"]
        items = []
        for i, t in enumerate(tps):
            lib = INITIATIVE_LIBRARY[t["column"]]
            items.append({"key": t["column"], "name": lib["name"], "owner": lib["owner"], "timing": quarters[i],
                          "priority": "High" if i < 2 else "Medium", "touchpoint": t["label"],
                          "lift": t["opportunity"], "n_low": t["n_low"]})
        return items
    return _memo("roadmap", None, build)


def roadmap_reach(items: list[dict]) -> int:
    df = dataset()["df"]
    cols = [i["key"] for i in items]
    if not cols:
        return 0
    return int(((df[cols] >= 1) & (df[cols] <= 2)).any(axis=1).sum())


# ================================================================== exports
def report_rows() -> list[tuple]:
    ov = overview("All classes")
    rows = [(m["title"], m["value"], m["note"]) for m in ov["metrics"]]
    for t in sorted(touchpoint_stats(dataset()["df"]), key=lambda t: t["mean"] or 0, reverse=True):
        rows.append((f"Rating: {t['label']}", f"{t['mean']:.2f} / 5" if t["mean"] else "—",
                     f"Satisfaction gap {fmt_pts(t['gap_pts'])}"))
    for p in ov["split"]:
        rows.append((p["label"], fmt_pct(p["pct"]), f"{p['count']:,} passengers"))
    return rows
