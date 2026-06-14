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
from dash import Dash, Input, Output, State, dcc, html

from rgb_evo_view.run_loader import LoadedRun, load_run
from rgb_evo_view.simulation import Frame
from visualizer.interactive_model import build_frame_index, colors_to_hex

# Dark field to match the GIF renderer; markers carry the only real color.
_FIELD_BG = "#0d0d12"
_PANEL_BG = "#15151c"
_FONT = "#e6e6ea"
_MUTED = "#9a9aa2"

# Playback speeds: label -> (Interval period in ms, frames advanced per tick).
# Slow speeds lengthen the period; fast speeds stride over frames at a fixed,
# smooth period so we don't fire callbacks faster than the browser can redraw.
_SPEEDS = {
    "0.5×": {"period": 130, "stride": 1},
    "1×": {"period": 65, "stride": 1},
    "2×": {"period": 65, "stride": 2},
    "4×": {"period": 65, "stride": 4},
}
_DEFAULT_SPEED = "1×"

# Playback dwells on the two end-of-cycle frames, mirroring the GIF renderer's
# holds (see visualizer/animate.py): the last walk frame -- the survivors, just
# before they mate -- is held longest, and the mate frame -- the newborns,
# before next cycle's food lands -- a little less.  These match the GIF's
# cycle_end_seconds / mate_seconds defaults (2.0s / 1.0s).
_SURVIVORS_HOLD_MS = 2000
_MATE_HOLD_MS = 1000


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


def _slider_row(label: str, slider: dcc.Slider) -> html.Div:
    return html.Div(
        style={"display": "flex", "alignItems": "center", "gap": "10px", "margin": "2px 0"},
        children=[
            html.Span(label, style={"width": "48px", "color": _MUTED, "fontSize": "12px"}),
            html.Div(slider, style={"flex": "1 1 auto"}),
        ],
    )


def _controls(run: LoadedRun) -> html.Div:
    """The bottom control bar: Play, speed, and the two scrub sliders."""
    last_cycle = max(run.num_cycles - 1, 0)
    last_tick = run.steps_per_cycle
    tooltip = {"placement": "bottom", "always_visible": False}
    return html.Div(
        style={
            "flex": "0 0 auto",
            "padding": "8px 16px",
            "backgroundColor": _PANEL_BG,
            "borderTop": "1px solid #22222a",
        },
        children=[
            # Interval drives playback; starts disabled (paused).
            dcc.Interval(
                id="tick-timer",
                interval=_SPEEDS[_DEFAULT_SPEED]["period"],
                disabled=True,
            ),
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "14px", "marginBottom": "4px"},
                children=[
                    html.Button("▶ Play", id="play", n_clicks=0, style={"minWidth": "84px"}),
                    html.Span("Speed", style={"color": _MUTED, "fontSize": "12px"}),
                    dcc.Dropdown(
                        id="speed",
                        options=[{"label": k, "value": k} for k in _SPEEDS],
                        value=_DEFAULT_SPEED,
                        clearable=False,
                        style={"width": "90px", "color": "#111"},
                    ),
                ],
            ),
            _slider_row(
                "cycle",
                dcc.Slider(
                    id="cycle-slider",
                    min=0,
                    max=last_cycle,
                    step=1,
                    value=0,
                    marks={0: "0", last_cycle: str(last_cycle)},
                    tooltip=tooltip,
                ),
            ),
            _slider_row(
                "tick",
                dcc.Slider(
                    id="tick-slider",
                    min=0,
                    max=last_tick,
                    step=1,
                    value=0,
                    marks={0: "0", last_tick: "mate"},
                    tooltip=tooltip,
                ),
            ),
        ],
    )


def make_app(run: LoadedRun) -> Dash:
    """Build the Dash app for a loaded run.

    The two sliders (cycle, tick) are the single source of truth for the
    current frame.  Playback advances them on an Interval; the scatter is a
    pure function of their values.  Keeping the render callback read-only on
    the sliders (it only outputs the figure) avoids any feedback loop with the
    playback callback, which writes them.
    """
    app = Dash(__name__)
    # Kill the browser's default body margin and paint the page the field color,
    # so there's no white band around the app.
    app.index_string = f"""<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}<title>{{%title%}}</title>{{%favicon%}}{{%css%}}
        <style>html, body {{ margin: 0; padding: 0; background: {_FIELD_BG}; }}</style>
    </head>
    <body>{{%app_entry%}}<footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer></body>
</html>"""
    frame_index = build_frame_index(run.frames)
    ticks_per_cycle = run.steps_per_cycle + 1  # walk ticks 0..steps-1 plus the mate frame
    total = len(run.frames)

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
                figure=world_figure(run.frames[0], run.world_size),
                config={"responsive": True, "displayModeBar": False},
                style={"flex": "1 1 auto", "minHeight": 0},
            ),
            _legend_bar(),
            _controls(run),
        ],
    )

    @app.callback(
        Output("world", "figure"),
        Input("cycle-slider", "value"),
        Input("tick-slider", "value"),
    )
    def _render(cycle: int, tick: int) -> go.Figure:
        idx = frame_index.index_of(int(cycle), int(tick))
        return world_figure(run.frames[idx], run.world_size)

    @app.callback(
        Output("tick-timer", "disabled"),
        Output("play", "children"),
        Input("play", "n_clicks"),
        State("tick-timer", "disabled"),
        prevent_initial_call=True,
    )
    def _toggle_play(_n_clicks: int, disabled: bool) -> tuple[bool, str]:
        now_paused = not disabled
        return now_paused, ("▶ Play" if now_paused else "⏸ Pause")

    last_walk_tick = run.steps_per_cycle - 1  # survivors, just before mating
    mate_tick = run.steps_per_cycle  # newborns, before next cycle's food

    @app.callback(
        Output("tick-timer", "interval"),
        Input("speed", "value"),
        Input("tick-slider", "value"),
    )
    def _interval_period(speed: str, tick: int) -> int:
        # Hold on the two end-of-cycle frames; changing the interval restarts the
        # countdown, so landing on them dwells before playback resumes.
        if int(tick) == last_walk_tick:
            return _SURVIVORS_HOLD_MS
        if int(tick) == mate_tick:
            return _MATE_HOLD_MS
        return _SPEEDS[speed]["period"]

    @app.callback(
        Output("cycle-slider", "value"),
        Output("tick-slider", "value"),
        Input("tick-timer", "n_intervals"),
        State("cycle-slider", "value"),
        State("tick-slider", "value"),
        State("speed", "value"),
        prevent_initial_call=True,
    )
    def _advance(_n: int, cycle: int, tick: int, speed: str) -> tuple[int, int]:
        stride = _SPEEDS[speed]["stride"]
        pos = (int(cycle) * ticks_per_cycle + int(tick) + stride) % total
        new_cycle, new_tick = divmod(pos, ticks_per_cycle)
        return new_cycle, new_tick

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
