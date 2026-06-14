"""Interactive web viewer for a finished run (Dash + Plotly).

Replays a run's saved frame stream in the browser -- no re-simulation.  This
module owns the Dash app; the Dash-free math (frame indexing, color conversion,
palette sampling, flower rendering) lives in :mod:`visualizer.interactive_model`
and the run loading in :mod:`rgb_evo_view.run_loader`.

Run it::

    poetry run python -m visualizer.interactive            # newest run under runs/
    poetry run python -m visualizer.interactive runs/<ts>  # a specific run
    poetry run python -m visualizer.interactive --port 8060

The world scatter scales to fill its panel: the figure is ``autosize`` with no
fixed pixel dimensions, the ``dcc.Graph`` is responsive and stretches to the
viewport, and equal-axis scaling keeps the spatial map undistorted (so a
non-square panel letterboxes rather than warping distances).
"""

from __future__ import annotations

import argparse

import plotly.graph_objects as go
from dash import Dash, dcc, html

from rgb_evo_view.run_loader import LoadedRun, load_run
from rgb_evo_view.simulation import Frame
from visualizer.interactive_model import colors_to_hex

# Dark field to match the GIF renderer; markers carry the only real color.
_FIELD_BG = "#0d0d12"
_FONT = "#e6e6ea"
_MUTED = "#9a9aa2"


def _frame_title(frame: Frame) -> str:
    if frame.population:
        r, g, b = (frame.creature_colors.mean(axis=0) * 255).round().astype(int)
        mean = f"mean RGB ({r},{g},{b})"
    else:
        mean = "mean RGB (—)"
    return f"cycle {frame.cycle}  ·  {frame.phase}  ·  pop {frame.population}  ·  {mean}"


def world_figure(frame: Frame, world_size: tuple[float, float]) -> go.Figure:
    """Scatter the world for one frame: food as squares, creatures as circles.

    Each marker is painted with its own genome color.  The figure is autosized
    (no fixed width/height) and uses equal-axis scaling so the responsive Graph
    can fill its panel without distorting the map.
    """
    width, height = world_size
    fig = go.Figure()

    fig.add_trace(
        go.Scattergl(
            x=frame.food_positions[:, 0],
            y=frame.food_positions[:, 1],
            mode="markers",
            marker={"symbol": "square", "size": 7, "color": colors_to_hex(frame.food_colors)},
            name="food",
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scattergl(
            x=frame.creature_positions[:, 0],
            y=frame.creature_positions[:, 1],
            mode="markers",
            marker={
                "symbol": "circle",
                "size": 10,
                "color": colors_to_hex(frame.creature_colors),
                "line": {"color": "white", "width": 0.5},
            },
            name="creatures",
            hoverinfo="skip",
        )
    )

    axis = {
        "showgrid": False,
        "zeroline": False,
        "showticklabels": False,
        "constrain": "domain",
    }
    fig.update_layout(
        autosize=True,
        margin={"l": 8, "r": 8, "t": 36, "b": 8},
        paper_bgcolor=_FIELD_BG,
        plot_bgcolor=_FIELD_BG,
        font={"color": _FONT},
        showlegend=False,
        title={"text": _frame_title(frame), "x": 0.5, "xanchor": "center"},
        xaxis={**axis, "range": [0, width]},
        # Equal-axis scaling: y units match x so the world isn't stretched.
        yaxis={**axis, "range": [0, height], "scaleanchor": "x", "scaleratio": 1},
    )
    return fig


def _legend_bar() -> html.Div:
    """A lightweight, static caption below the map (never overlaps it).

    Conveys the two marker shapes and the core idea -- a creature's color *is*
    its genome.  Not a Plotly data legend, whose single swatch color would be
    arbitrary and misleading when every dot carries its own color.
    """
    return html.Div(
        style={
            "flex": "0 0 auto",
            "padding": "6px 12px",
            "textAlign": "center",
            "fontSize": "13px",
            "color": _MUTED,
            "backgroundColor": _FIELD_BG,
            "borderTop": "1px solid #22222a",
        },
        children=[
            html.Span("■ food", style={"marginRight": "18px"}),
            html.Span("● creatures", style={"marginRight": "18px"}),
            html.Span("·", style={"marginRight": "18px"}),
            html.I("colors are genes", style={"color": _FONT}),
        ],
    )


def make_app(run: LoadedRun) -> Dash:
    """Build the Dash app for a loaded run.

    Step 4: a static, responsive world scatter of the first frame.  Scrub
    sliders, playback, the summary tab, and the flower garden are layered on in
    later steps.
    """
    app = Dash(__name__)
    first = run.frames[0]

    app.layout = html.Div(
        style={
            "height": "100vh",
            "margin": 0,
            "display": "flex",
            "flexDirection": "column",
            "backgroundColor": _FIELD_BG,
        },
        children=[
            dcc.Graph(
                id="world",
                figure=world_figure(first, run.world_size),
                config={"responsive": True, "displayModeBar": False},
                style={"flex": "1 1 auto", "minHeight": 0},
            ),
            _legend_bar(),
        ],
    )
    return app


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "run_dir",
        nargs="?",
        default=None,
        help="A run folder under runs/ (defaults to the most recent).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to serve on.")
    parser.add_argument("--port", type=int, default=8050, help="Port to serve on.")
    parser.add_argument("--debug", action="store_true", help="Run Dash in debug mode.")
    args = parser.parse_args()

    if args.run_dir is None:
        from rgb_evo_view.run_loader import latest_run

        run_dir = latest_run()
        print(f"[viewer] no run given; using most recent: {run_dir}")
    else:
        run_dir = args.run_dir

    run = load_run(run_dir)
    print(
        f"[viewer] {len(run.frames)} frames · {run.num_cycles} cycles · serving on http://{args.host}:{args.port}"
    )
    app = make_app(run)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
