<a id="rgb_evo_view.creature"></a>

# rgb\_evo\_view.creature

The Creature: a colored dot that wanders, eats, starves, and breeds.

<a id="rgb_evo_view.creature.Creature"></a>

## Creature Objects

```python
class Creature()
```

One organism in the simulation.

Its ``genome`` is its color and its entire heritable identity.  During the
walk phase it moves each tick (paying a move cost charged by the simulation)
and tops its energy up by eating food it bumps into; if energy hits zero it
dies and stops moving for the rest of the cycle.

<a id="rgb_evo_view.creature.Creature.move"></a>

#### move

```python
def move(world: World, rng: np.random.Generator) -> None
```

Take one step, keeping the creature inside the world's bounds.

<a id="rgb_evo_view.creature.Creature.consume"></a>

#### consume

```python
def consume(food: FoodResource,
            model: OverlapModel,
            gamma: float,
            min_overlap: float = 0.0) -> float
```

Eat a food: gain energy proportional to how well our colors match.

Marks the food consumed and returns the energy gained (also added to this
creature's running totals).
