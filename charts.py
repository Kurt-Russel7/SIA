"""SVG geometry helpers for the hand-drawn charts (no charting library needed)."""

import math

VIEW_W, VIEW_H = 700, 250


def _smooth_path(points):
    """Smooth SVG path through points (Catmull-Rom converted to cubic Bézier)."""
    d = f"M{points[0][0]:.1f} {points[0][1]:.1f}"
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1, p2 = points[i], points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f} {c1[1]:.1f},{c2[0]:.1f} {c2[1]:.1f},{p2[0]:.1f} {p2[1]:.1f}"
    return d


def line_chart(labels, series, x0=28, x1=672, top=10, bottom=240, vmin=0, vmax=100):
    """Geometry for a multi-series line chart.

    series: {name: [value or None, ...]} aligned with labels. None values are skipped.
    Returns paths in viewBox units plus HTML-positioned points/labels as percentages,
    so text and markers don't stretch with the responsive SVG.
    """
    n = len(labels)
    step = (x1 - x0) / (n - 1) if n > 1 else 0
    scale_y = lambda v: bottom - (v - vmin) / (vmax - vmin) * (bottom - top)  # noqa: E731

    out = {"series": {}, "x_labels": [], "y_labels": [], "gridlines": []}
    for i, label in enumerate(labels):
        out["x_labels"].append({"left": (x0 + i * step) / VIEW_W * 100, "text": label})
    for k in range(5):
        v = vmin + (vmax - vmin) * k / 4
        y = scale_y(v)
        out["gridlines"].append(y)
        out["y_labels"].append({"top": y / VIEW_H * 100, "text": f"{v:.0f}%"})

    for name, values in series.items():
        pts = [(x0 + i * step, scale_y(v), v, labels[i]) for i, v in enumerate(values) if v is not None]
        if len(pts) < 2:
            continue
        xy = [(p[0], p[1]) for p in pts]
        line = _smooth_path(xy)
        out["series"][name] = {
            "line": line,
            "area": f"{line} L{xy[-1][0]:.1f} {bottom} L{xy[0][0]:.1f} {bottom} Z",
            "points": [{"left": p[0] / VIEW_W * 100, "top": p[1] / VIEW_H * 100,
                        "title": f"{name} · {p[3]}: {p[2]:.1f}% satisfied"} for p in pts],
        }
    out.update(x0=x0, x1=x1)
    return out


def donut(parts, radius=48, gap=4):
    """stroke-dasharray / offset for each donut slice from percentages."""
    circumference = 2 * math.pi * radius
    out, offset = [], 0.0
    for part in parts:
        length = part["pct"] / 100 * circumference
        if length > 0:
            out.append({"color": part["color"],
                        "dash": f"{max(length - gap, 0.1):.1f} {circumference:.1f}",
                        "offset": f"{-offset:.1f}"})
        offset += length
    return out
