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

import numpy as np
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, ctx, dcc, html
from dash.exceptions import PreventUpdate
from plotly.subplots import make_subplots

from rgb_evo_view.run_loader import LoadedRun, load_run
from rgb_evo_view.simulation import Frame
from visualizer.interactive_model import ascii_flowers, build_frame_index, colors_to_hex, sample_palette

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

_ACCENT = "#7b5cff"

# Flower garden: how many living-creature colors to sample, tiled this many
# across.  9 colors -> a 3x3 grid of ASCII tulips.
_GARDEN_SAMPLES = 9
_GARDEN_PER_ROW = 3
_GARDEN_WIDTH = 360


def _garden_panel_style(is_open: bool) -> dict:
    """Slide-out garden panel: parked off the right edge until opened."""
    return {
        "position": "absolute",
        "top": "44px",
        "right": 0,
        "bottom": 0,
        "width": f"{_GARDEN_WIDTH}px",
        "zIndex": 18,
        "backgroundColor": _PANEL_BG,
        "borderLeft": "1px solid #2a2a33",
        "boxShadow": "-8px 0 24px rgba(0,0,0,0.4)",
        "display": "flex",
        "flexDirection": "column",
        "transition": "transform 0.28s ease",
        "transform": "translateX(0)" if is_open else f"translateX({_GARDEN_WIDTH + 12}px)",
    }


def _view_btn_style(active: bool) -> dict:
    """Segmented-control button: filled accent when active, quiet otherwise."""
    return {
        "border": "none",
        "borderRadius": "6px",
        "padding": "5px 16px",
        "fontSize": "13px",
        "cursor": "pointer",
        "backgroundColor": _ACCENT if active else "transparent",
        "color": "white" if active else _MUTED,
    }


def _color_swatch(hex_color: str, size: int = 18) -> html.Div:
    """A small rounded color chip."""
    return html.Div(
        style={
            "width": f"{size}px",
            "height": f"{size}px",
            "borderRadius": "4px",
            "backgroundColor": hex_color,
            "border": "1px solid #444",
            "flex": "0 0 auto",
        }
    )


def _frame_title(frame: Frame) -> str:
    if frame.population:
        r, g, b = (frame.creature_colors.mean(axis=0) * 255).round().astype(int)
        mean = f"mean RGB ({r},{g},{b})"
    else:
        mean = "mean RGB (—)"
    return f"cycle {frame.cycle}  ·  {frame.phase}  ·  pop {frame.population}  ·  {mean}"


def _world_header(frame: Frame) -> list:
    """The playback title line plus a swatch of the current mean color."""
    children: list = [html.Span(_frame_title(frame))]
    if frame.population:
        mean_hex = colors_to_hex([frame.creature_colors.mean(axis=0)])[0]
        children.append(_color_swatch(mean_hex))
    return children


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
        margin={"l": 8, "r": 8, "t": 8, "b": 8},
        paper_bgcolor=_FIELD_BG,
        plot_bgcolor=_FIELD_BG,
        font={"color": _FONT},
        showlegend=False,
        xaxis={**axis, "range": [0, width]},
        # Equal-axis scaling: y units match x so the world isn't stretched.
        yaxis={**axis, "range": [0, height], "scaleanchor": "x", "scaleratio": 1},
    )
    return fig


# Channel-line colors for the drift chart: legible reds/greens/blues on dark.
_CHANNEL_COLORS = {"R": "#ff6b6b", "G": "#51cf66", "B": "#4dabf7"}
_GRID = "#22222a"


def summary_figure(history: list[dict]) -> go.Figure:
    """The run's drift chart: mean R/G/B per cycle, plus population & deaths.

    A Plotly reimplementation of :func:`visualizer.stats.plot_history` for the
    Summary tab (the static version stays matplotlib for the PNG/GIF).
    """
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.62, 0.38],
        subplot_titles=("Population mean color over time", "Population & deaths"),
    )

    # Shift cycle indices by +1 so the founding row (stored as cycle -1, the
    # initial population before any selection) reads as the 0th / starting cycle
    # rather than "-1".  Keeps the founding point on the line; the axis stays
    # "cycle" (it's cycles, not generations -- parents persist across cycles).
    cycles = [h["cycle"] + 1 for h in history]
    channels = list(zip(*[h["mean_rgb"] for h in history], strict=True))
    for values, name in zip(channels, ("R", "G", "B"), strict=True):
        fig.add_trace(
            go.Scatter(
                x=cycles, y=values, mode="lines", name=name, line={"color": _CHANNEL_COLORS[name], "width": 2}
            ),
            row=1,
            col=1,
        )
    fig.add_trace(
        go.Scatter(
            x=cycles,
            y=[h["survivors"] for h in history],
            mode="lines",
            name="survivors",
            line={"color": _FONT, "width": 2},
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=cycles,
            y=[h["deaths"] for h in history],
            mode="lines",
            name="deaths",
            line={"color": _MUTED, "width": 2, "dash": "dash"},
        ),
        row=2,
        col=1,
    )

    fig.update_yaxes(range=[0, 1], title_text="mean channel", row=1, col=1)
    fig.update_yaxes(title_text="creatures", row=2, col=1)
    fig.update_xaxes(title_text="cycle", row=2, col=1)
    fig.update_xaxes(gridcolor=_GRID, zeroline=False)
    fig.update_yaxes(gridcolor=_GRID, zeroline=False)
    fig.update_annotations(font={"color": _FONT, "size": 14})  # subplot titles
    fig.update_layout(
        autosize=True,
        paper_bgcolor=_FIELD_BG,
        plot_bgcolor=_FIELD_BG,
        font={"color": _FONT},
        margin={"l": 56, "r": 24, "t": 36, "b": 40},
        legend={"orientation": "h", "y": 1.08, "x": 1, "xanchor": "right"},
    )
    return fig


def _stat(label: str, value: str) -> html.Div:
    return html.Div(
        style={"textAlign": "center"},
        children=[
            html.Div(value, style={"fontSize": "20px", "color": _FONT}),
            html.Div(label, style={"fontSize": "11px", "color": _MUTED, "letterSpacing": "0.04em"}),
        ],
    )


def _summary_panel(run: LoadedRun) -> html.Div:
    """The Summary tab: a stats strip over the drift chart."""
    history = run.history
    if not history:
        return html.Div("No history recorded for this run.", style={"padding": "24px", "color": _MUTED})

    founding, last = history[0], history[-1]
    start_hex = colors_to_hex([founding["mean_rgb"]])[0]
    final_hex = colors_to_hex([last["mean_rgb"]])[0]

    def _color_stat(label: str, hex_color: str) -> html.Div:
        return html.Div(
            style={"display": "flex", "alignItems": "center", "gap": "10px"},
            children=[_color_swatch(hex_color, size=26), _stat(label, hex_color)],
        )

    stats = html.Div(
        style={
            "flex": "0 0 auto",
            "display": "flex",
            "justifyContent": "center",
            "gap": "40px",
            "alignItems": "center",
            "padding": "14px",
        },
        children=[
            _stat("cycles", str(run.num_cycles)),
            _stat("founding pop", str(founding["survivors"])),
            _stat("final pop", str(last["survivors"])),
            _color_stat("starting mean color", start_hex),
            _color_stat("final mean color", final_hex),
        ],
    )

    return html.Div(
        style={"display": "flex", "flexDirection": "column", "height": "100%"},
        children=[
            stats,
            dcc.Graph(
                id="summary-chart",
                figure=summary_figure(history),
                config={"responsive": True, "displayModeBar": False},
                style={"flex": "1 1 auto", "minHeight": 0},
            ),
        ],
    )


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
                    html.Button("Play", id="play", n_clicks=0, style={"minWidth": "84px"}),
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
    garden_rng = np.random.default_rng()  # unseeded: each draw/resample differs

    # Both views stay mounted; the view switcher toggles their display.  That
    # keeps the replay components (and their playback state) alive while on
    # Summary, rather than tearing them down and resetting on every switch.
    replay_view = html.Div(
        id="replay-view",
        style={"flex": "1 1 auto", "minHeight": 0, "display": "flex", "flexDirection": "column"},
        children=[
            html.Div(
                id="world-title",
                style={
                    "flex": "0 0 auto",
                    "display": "flex",
                    "justifyContent": "center",
                    "alignItems": "center",
                    "gap": "10px",
                    "padding": "8px",
                    "fontSize": "18px",
                    "color": _FONT,
                },
                children=_world_header(run.frames[0]),
            ),
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
    summary_view = html.Div(
        id="summary-view",
        style={"flex": "1 1 auto", "minHeight": 0, "display": "none", "flexDirection": "column"},
        children=[_summary_panel(run)],
    )

    # A small segmented control floating in the top-right, over the dark field --
    # no full-width tab bar to cut a grey band against the plot.
    view_switch = html.Div(
        style={
            "position": "absolute",
            "top": "10px",
            "right": "14px",
            "zIndex": 20,
            "display": "flex",
            "gap": "2px",
            "padding": "3px",
            "borderRadius": "9px",
            "backgroundColor": _PANEL_BG,
            "border": "1px solid #2a2a33",
        },
        children=[
            html.Button("Replay", id="btn-replay", n_clicks=0, style=_view_btn_style(True)),
            html.Button("Summary", id="btn-summary", n_clicks=0, style=_view_btn_style(False)),
        ],
    )

    # The garden toggle floats just under the view switch; the panel slides out
    # from the right edge beneath it.  The toggle stays above the panel so it
    # can close it again.
    garden_toggle = html.Button(
        "Garden",
        id="garden-toggle",
        n_clicks=0,
        style={
            "position": "absolute",
            "top": "52px",
            "right": "14px",
            "zIndex": 22,
            "border": "1px solid #2a2a33",
            "borderRadius": "8px",
            "padding": "5px 12px",
            "fontSize": "13px",
            "cursor": "pointer",
            "backgroundColor": _PANEL_BG,
            "color": _FONT,
        },
    )
    garden_panel = html.Div(
        id="garden-panel",
        style=_garden_panel_style(False),
        children=[
            html.Div(
                style={
                    "flex": "0 0 auto",
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "12px",
                    "padding": "10px 12px 6px",
                },
                children=[
                    html.Span("Flower garden", style={"color": _FONT, "fontSize": "14px"}),
                    html.Button(
                        "Resample",
                        id="garden-resample",
                        n_clicks=0,
                        style={
                            "border": "none",
                            "borderRadius": "6px",
                            "padding": "4px 12px",
                            "fontSize": "12px",
                            "cursor": "pointer",
                            "backgroundColor": _ACCENT,
                            "color": "white",
                        },
                    ),
                ],
            ),
            dcc.Markdown(
                id="garden-content",
                dangerously_allow_html=True,
                style={
                    "flex": "1 1 auto",
                    "minHeight": 0,
                    "overflowY": "auto",
                    "padding": "0 12px 12px",
                    "fontFamily": "monospace",
                    "fontSize": "11px",
                    "lineHeight": "1.1",
                    "color": _FONT,
                },
            ),
        ],
    )

    app.layout = html.Div(
        style={
            "position": "relative",
            "height": "100vh",
            "margin": 0,
            "display": "flex",
            "flexDirection": "column",
            "backgroundColor": _FIELD_BG,
        },
        children=[
            dcc.Store(id="garden-open", data=False),
            view_switch,
            garden_toggle,
            garden_panel,
            replay_view,
            summary_view,
        ],
    )

    @app.callback(
        Output("replay-view", "style"),
        Output("summary-view", "style"),
        Output("btn-replay", "style"),
        Output("btn-summary", "style"),
        Input("btn-replay", "n_clicks"),
        Input("btn-summary", "n_clicks"),
    )
    def _switch_view(_r: int, _s: int) -> tuple[dict, dict, dict, dict]:
        on_summary = ctx.triggered_id == "btn-summary"
        base = {"flex": "1 1 auto", "minHeight": 0, "flexDirection": "column"}
        shown, hidden = {**base, "display": "flex"}, {**base, "display": "none"}
        replay_style, summary_style = (hidden, shown) if on_summary else (shown, hidden)
        return (
            replay_style,
            summary_style,
            _view_btn_style(not on_summary),
            _view_btn_style(on_summary),
        )

    @app.callback(
        Output("world", "figure"),
        Output("world-title", "children"),
        Input("cycle-slider", "value"),
        Input("tick-slider", "value"),
    )
    def _render(cycle: int, tick: int) -> tuple[go.Figure, list]:
        frame = run.frames[frame_index.index_of(int(cycle), int(tick))]
        return world_figure(frame, run.world_size), _world_header(frame)

    @app.callback(
        Output("tick-timer", "disabled"),
        Output("play", "children"),
        Input("play", "n_clicks"),
        State("tick-timer", "disabled"),
        prevent_initial_call=True,
    )
    def _toggle_play(_n_clicks: int, disabled: bool) -> tuple[bool, str]:
        now_paused = not disabled
        return now_paused, ("Play" if now_paused else "Pause")

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

    @app.callback(
        Output("garden-panel", "style"),
        Output("garden-open", "data"),
        Input("garden-toggle", "n_clicks"),
        State("garden-open", "data"),
        prevent_initial_call=True,
    )
    def _toggle_garden(_n: int, is_open: bool) -> tuple[dict, bool]:
        now_open = not is_open
        return _garden_panel_style(now_open), now_open

    @app.callback(
        Output("garden-content", "children"),
        Input("cycle-slider", "value"),
        Input("tick-slider", "value"),
        Input("garden-resample", "n_clicks"),
        Input("garden-open", "data"),
        State("garden-open", "data"),
    )
    def _garden(cycle: int, tick: int, _resample: int, _open_in: bool, is_open: bool) -> str:
        # Skip the per-frame redraw while the panel is closed (the common case
        # during playback); still draw on the initial load, on resample, and
        # when the panel is opened.
        if ctx.triggered_id in ("cycle-slider", "tick-slider") and not is_open:
            raise PreventUpdate
        frame = run.frames[frame_index.index_of(int(cycle), int(tick))]
        palette = sample_palette(frame, _GARDEN_SAMPLES, rng=garden_rng)
        return ascii_flowers(palette, frame.cycle, per_row=_GARDEN_PER_ROW)

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
