"""SkyArch — Passenger intelligence dashboard (Flask version).

All figures are computed live from the passenger CSV files in ./data
(see analytics.py). Upload a new CSV on the Data workspace page to refresh them.
"""

import csv
import io
import os

from flask import (Flask, Response, abort, flash, redirect, render_template,
                   request, session, url_for)

import analytics as a
import charts
import data as d
from icons import icon

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB upload limit


@app.context_processor
def inject_globals():
    return {"nav_items": d.NAV_ITEMS, "icon": icon, "meta": a.meta(),
            "fmt_pct": a.fmt_pct, "fmt_pts": a.fmt_pts}


def pick(value, options, default):
    """Return `value` if it is one of `options`, else `default` (guards query params)."""
    return value if value in options else default


# --------------------------------------------------------------------- pages
@app.route("/")
def overview():
    cls = pick(request.args.get("cls"), a.CLASS_FILTERS, "All classes")
    ov = a.overview(cls)
    return render_template(
        "overview.html",
        active="Overview",
        cls=cls,
        classes=a.CLASS_FILTERS,
        ov=ov,
        chart=charts.line_chart(ov["age_labels"], ov["age_series"]),
        donut=charts.donut(ov["split"]),
    )


@app.route("/data")
def data_workspace():
    return render_template(
        "data_workspace.html",
        active="Data workspace",
        copy=d.PAGE_COPY["Data workspace"],
        dw=a.data_workspace(),
        required=a.REQUIRED_COLUMNS,
    )


@app.post("/data/import")
def import_data():
    file = request.files.get("dataset")
    mode = pick(request.form.get("mode"), ["replace", "append"], "append")
    if not file or not file.filename:
        flash("Choose a CSV file to import.", "error")
        return redirect(url_for("data_workspace"))
    if not file.filename.lower().endswith(".csv"):
        flash("Only .csv files are supported.", "error")
        return redirect(url_for("data_workspace"))

    df, error = a.validate_upload(file)
    if error:
        flash(error, "error")
        return redirect(url_for("data_workspace"))

    a.save_upload(df, file.filename, mode)
    verb = "replaced the dataset" if mode == "replace" else "was added to the dataset"
    flash(f"{file.filename} {verb} — {len(df):,} rows. All dashboards have been recalculated.", "success")
    return redirect(url_for("data_workspace"))


@app.post("/data/reset")
def reset_data():
    a.reset_dataset()
    flash("Restored the original dataset (train.csv + test.csv).", "success")
    return redirect(url_for("data_workspace"))


@app.route("/services")
def service_analytics():
    selected = pick(request.args.get("filter"), a.SERVICE_FILTERS, "All passengers")
    return render_template(
        "service_analytics.html",
        active="Service analytics",
        copy=d.PAGE_COPY["Service analytics"],
        filters=a.SERVICE_FILTERS,
        selected=selected,
        sv=a.services(selected),
    )


@app.route("/segments")
def passenger_segments():
    names = list(a.SEGMENT_MASKS)
    selected = pick(request.args.get("segment"), names, names[0])
    return render_template(
        "passenger_segments.html",
        active="Passenger segments",
        copy=d.PAGE_COPY["Passenger segments"],
        sg=a.segments(selected),
    )


@app.route("/architecture")
def architecture():
    view = pick(request.args.get("view"), d.ARCH_VIEWS, d.ARCH_VIEWS[0])
    return render_template(
        "architecture.html",
        active="Architecture",
        copy=d.PAGE_COPY["Architecture"],
        views=d.ARCH_VIEWS,
        view=view,
        layers=d.ARCH_LAYERS,
        z_columns=d.ZACHMAN_COLUMNS,
        z_rows=d.ZACHMAN_ROWS,
        z_cells=d.ZACHMAN_CELLS,
        phases=d.TOGAF_PHASES,
    )


def completed_initiatives():
    return session.get("completed_keys", [])


@app.route("/roadmap")
def roadmap():
    items = a.roadmap_items()
    keys = [i["key"] for i in items]
    completed = [k for k in completed_initiatives() if k in keys]
    owners = {i["owner"] for i in items}
    return render_template(
        "roadmap.html",
        active="Improvement roadmap",
        copy=d.PAGE_COPY["Improvement roadmap"],
        items=items,
        completed=completed,
        progress=round(len(completed) / len(items) * 100) if items else 0,
        done=len(completed),
        owners=len(owners),
        reach=a.roadmap_reach(items),
        total=a.meta()["rows"],
    )


@app.post("/roadmap/toggle")
def toggle_initiative():
    key = request.form.get("key")
    if key in {i["key"] for i in a.roadmap_items()}:
        completed = completed_initiatives()
        completed = [k for k in completed if k != key] if key in completed else completed + [key]
        session["completed_keys"] = completed
    return redirect(url_for("roadmap"))


# ------------------------------------------------------------------- exports
def csv_response(filename, header, rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.route("/report.csv")
def download_report():
    return csv_response("skyarch-insight-report.csv", ["Metric", "Value", "Note"], a.report_rows())


def _export_services():
    rows = [(t["label"], t["area"], f"{t['mean']:.2f}", a.fmt_pct(t["share_high"]), a.fmt_pts(t["gap_pts"]),
             t["status"]) for t in a.services("All passengers")["rows"]]
    return ["Touchpoint", "Journey area", "Avg rating", "Rated 4-5", "Satisfaction gap", "Status"], rows


def _export_segments():
    names = list(a.SEGMENT_MASKS)
    rows = [(c["name"], c["count"], a.fmt_pct(c["satisfaction"]), c["description"])
            for c in a.segments(names[0])["cards"]]
    return ["Segment", "Passengers", "Satisfied", "Description"], rows


def _export_roadmap():
    done = completed_initiatives()
    rows = [(i["name"], i["touchpoint"], i["owner"], i["timing"], i["priority"], a.fmt_pts(i["lift"]),
             "Yes" if i["key"] in done else "No") for i in a.roadmap_items()]
    return ["Initiative", "Touchpoint", "Owner", "Timing", "Priority", "Potential lift", "Completed"], rows


EXPORTS = {
    "data": lambda: (["Step", "Detail", "Status"], a.data_workspace()["pipeline"]),
    "services": _export_services,
    "segments": _export_segments,
    "architecture": lambda: (["Layer", "Capability", "Components"], [row[:3] for row in d.ARCH_LAYERS]),
    "roadmap": _export_roadmap,
}


@app.route("/export/<page>.csv")
def export_view(page):
    if page not in EXPORTS:
        abort(404)
    header, rows = EXPORTS[page]()
    return csv_response(f"skyarch-{page}.csv", header, rows)


@app.errorhandler(413)
def too_large(_):
    flash("That file is larger than the 50 MB limit.", "error")
    return redirect(url_for("data_workspace"))


if __name__ == "__main__":
    app.run(debug=True)
