from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.grapher.grapher")
logger.debug("Loaded tool module: grapher.grapher")

from pathlib import Path
from app.utils.groq import tool

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # type: ignore
except Exception:
    plt = None


def _require():
    if plt is None:
        raise RuntimeError("matplotlib not installed")


def _save(out: str):
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(outp)
    plt.close()
    return str(outp.resolve())


def _setup(title: str = "", xlabel: str = "", ylabel: str = "", style: str = "", figsize: list[int] | None = None, dpi: int | None = None, grid: bool = False):
    if style:
        plt.style.use(style)
    if figsize:
        plt.figure(figsize=(figsize[0], figsize[1]))
    if dpi:
        plt.gcf().set_dpi(dpi)
    if title:
        plt.title(title)
    if xlabel:
        plt.xlabel(xlabel)
    if ylabel:
        plt.ylabel(ylabel)
    if grid:
        plt.grid(True, alpha=0.3)


@tool(
    name="graph_line",
    description="Plot a line chart.",
    params={
        "x": {"type": "array"},
        "y": {"type": "array"},
        "title": {"type": "string"},
        "xlabel": {"type": "string"},
        "ylabel": {"type": "string"},
        "out": {"type": "string"},
        "style": {"type": "string", "description": "Matplotlib style (optional)"},
        "figsize": {"type": "array", "description": "Figure size [w,h] (optional)"},
        "dpi": {"type": "integer", "description": "DPI (optional)"},
        "grid": {"type": "boolean", "description": "Show grid (optional)"},
    },
)
def graph_line(
    x: list,
    y: list,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    out: str = "graph.png",
    style: str = "",
    figsize: list[int] | None = None,
    dpi: int | None = None,
    grid: bool = False,
):
    _require()
    _setup(title=title, xlabel=xlabel, ylabel=ylabel, style=style, figsize=figsize, dpi=dpi, grid=grid)
    plt.plot(x, y)
    return _save(out)


@tool(
    name="graph_bar",
    description="Plot a bar chart.",
    params={
        "labels": {"type": "array"},
        "values": {"type": "array"},
        "title": {"type": "string"},
        "xlabel": {"type": "string"},
        "ylabel": {"type": "string"},
        "out": {"type": "string"},
        "style": {"type": "string", "description": "Matplotlib style (optional)"},
        "figsize": {"type": "array", "description": "Figure size [w,h] (optional)"},
        "dpi": {"type": "integer", "description": "DPI (optional)"},
        "grid": {"type": "boolean", "description": "Show grid (optional)"},
    },
)
def graph_bar(
    labels: list,
    values: list,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    out: str = "graph.png",
    style: str = "",
    figsize: list[int] | None = None,
    dpi: int | None = None,
    grid: bool = False,
):
    _require()
    _setup(title=title, xlabel=xlabel, ylabel=ylabel, style=style, figsize=figsize, dpi=dpi, grid=grid)
    plt.bar(labels, values)
    return _save(out)


@tool(
    name="graph_scatter",
    description="Plot a scatter chart.",
    params={
        "x": {"type": "array"},
        "y": {"type": "array"},
        "title": {"type": "string"},
        "xlabel": {"type": "string"},
        "ylabel": {"type": "string"},
        "out": {"type": "string"},
        "style": {"type": "string", "description": "Matplotlib style (optional)"},
        "figsize": {"type": "array", "description": "Figure size [w,h] (optional)"},
        "dpi": {"type": "integer", "description": "DPI (optional)"},
        "grid": {"type": "boolean", "description": "Show grid (optional)"},
    },
)
def graph_scatter(
    x: list,
    y: list,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    out: str = "graph.png",
    style: str = "",
    figsize: list[int] | None = None,
    dpi: int | None = None,
    grid: bool = False,
):
    _require()
    _setup(title=title, xlabel=xlabel, ylabel=ylabel, style=style, figsize=figsize, dpi=dpi, grid=grid)
    plt.scatter(x, y)
    return _save(out)


@tool(
    name="graph_hist",
    description="Plot a histogram.",
    params={
        "values": {"type": "array"},
        "bins": {"type": "integer"},
        "title": {"type": "string"},
        "xlabel": {"type": "string"},
        "ylabel": {"type": "string"},
        "out": {"type": "string"},
        "style": {"type": "string", "description": "Matplotlib style (optional)"},
        "figsize": {"type": "array", "description": "Figure size [w,h] (optional)"},
        "dpi": {"type": "integer", "description": "DPI (optional)"},
        "grid": {"type": "boolean", "description": "Show grid (optional)"},
    },
)
def graph_hist(
    values: list,
    bins: int = 10,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    out: str = "graph.png",
    style: str = "",
    figsize: list[int] | None = None,
    dpi: int | None = None,
    grid: bool = False,
):
    _require()
    _setup(title=title, xlabel=xlabel, ylabel=ylabel, style=style, figsize=figsize, dpi=dpi, grid=grid)
    plt.hist(values, bins=int(bins))
    return _save(out)


@tool(
    name="graph_pie",
    description="Plot a pie chart.",
    params={
        "labels": {"type": "array"},
        "values": {"type": "array"},
        "title": {"type": "string"},
        "out": {"type": "string"},
    },
)
def graph_pie(labels: list, values: list, title: str = "", out: str = "graph.png"):
    _require()
    _setup(title=title)
    plt.pie(values, labels=labels, autopct="%1.1f%%")
    return _save(out)


@tool(
    name="graph_box",
    description="Plot a box plot.",
    params={
        "values": {"type": "array"},
        "title": {"type": "string"},
        "ylabel": {"type": "string"},
        "out": {"type": "string"},
    },
)
def graph_box(values: list, title: str = "", ylabel: str = "", out: str = "graph.png"):
    _require()
    _setup(title=title, ylabel=ylabel)
    plt.boxplot(values)
    return _save(out)


@tool(
    name="graph_multi_line",
    description="Plot multiple lines on one chart.",
    params={
        "series": {"type": "array", "description": "List of {x, y, label}"},
        "title": {"type": "string"},
        "xlabel": {"type": "string"},
        "ylabel": {"type": "string"},
        "legend": {"type": "boolean"},
        "out": {"type": "string"},
    },
)
def graph_multi_line(series: list[dict], title: str = "", xlabel: str = "", ylabel: str = "", legend: bool = True, out: str = "graph.png"):
    _require()
    _setup(title=title, xlabel=xlabel, ylabel=ylabel)
    for s in series:
        plt.plot(s.get("x", []), s.get("y", []), label=s.get("label", ""))
    if legend:
        plt.legend()
    return _save(out)
