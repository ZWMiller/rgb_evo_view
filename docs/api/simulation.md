<a id="rgb_evo_view.simulation"></a>

# rgb\_evo\_view.simulation

The simulation manager: orchestrates the food -> walk -> mate cycle.

A run is a sequence of cycles.  Each cycle: scatter fresh food, refresh the
creatures' energy (a fresh ``starting_energy`` each cycle, or -- with
``energy.carryover_energy`` -- survivors keep last cycle's leftover so fitness
compounds), run the walk phase (every creature moves once per tick, paying a move
cost and eating what it touches; it dies if energy runs out), then clear the food
and let the survivors mate into the next generation.

The whole run is exposed as a generator of :class:`Frame` snapshots (one per
tick, plus one after each mating), which is the single source of truth: the
visualizer animates the frames, ``recording.save_frames`` persists them, and
:meth:`SimulationManager.run` simply drains them headlessly.  Output (a copy of
the config, the per-cycle ``history.json``, and the full frame log ``frames.npz``)
lands in a timestamped folder under ``output_dir``.

<a id="rgb_evo_view.simulation.Frame"></a>

## Frame Objects

```python
@dataclass(frozen=True)
class Frame()
```

An immutable snapshot of the world at one moment, for rendering.

<a id="rgb_evo_view.simulation.Frame.phase"></a>

#### phase

"walk" | "mate"

<a id="rgb_evo_view.simulation.Frame.creature_positions"></a>

#### creature\_positions

(N, 2)

<a id="rgb_evo_view.simulation.Frame.creature_colors"></a>

#### creature\_colors

(N, 3)

<a id="rgb_evo_view.simulation.Frame.food_positions"></a>

#### food\_positions

(M, 2)

<a id="rgb_evo_view.simulation.Frame.food_colors"></a>

#### food\_colors

(M, 3)

<a id="rgb_evo_view.simulation.SimulationManager"></a>

## SimulationManager Objects

```python
class SimulationManager()
```

Owns the world, the RNG, the population, and run output.

<a id="rgb_evo_view.simulation.SimulationManager.setup"></a>

#### setup

```python
def setup() -> Path
```

Create the output folder, seed the RNG, and build the founding population.

<a id="rgb_evo_view.simulation.SimulationManager.run"></a>

#### run

```python
def run() -> None
```

Run the whole simulation headlessly, discarding the rendered frames.

<a id="rgb_evo_view.simulation.SimulationManager.frames"></a>

#### frames

```python
def frames() -> Iterator[Frame]
```

Advance the simulation, yielding a snapshot after every tick and mating.
