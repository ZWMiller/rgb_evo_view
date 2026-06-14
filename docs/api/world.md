<a id="rgb_evo_view.world"></a>

# rgb\_evo\_view.world

The world: the box everything lives in, plus its spatial queries.

The world owns the population and the current food, knows how to keep a moving
creature inside its walls, and answers the two spatial questions the simulation
asks each cycle: "what food is this creature touching?" and "who is the nearest
creature to this one?".

<a id="rgb_evo_view.world.World"></a>

## World Objects

```python
class World()
```

A 2-D box holding creatures and food.

<a id="rgb_evo_view.world.World.food"></a>

#### food

```python
@food.setter
def food(food: list[FoodResource]) -> None
```

Set the current food and refresh the cached position array in step.

<a id="rgb_evo_view.world.World.random_position"></a>

#### random\_position

```python
def random_position(rng: np.random.Generator) -> np.ndarray
```

A uniformly random point inside the box.

<a id="rgb_evo_view.world.World.apply_boundary"></a>

#### apply\_boundary

```python
def apply_boundary(position: np.ndarray) -> np.ndarray
```

Bring a proposed position back inside the box per the boundary mode.

``reflect`` bounces off the walls, ``clamp`` sticks to them, and ``wrap``
teleports across to the opposite edge (a toroidal world).

<a id="rgb_evo_view.world.World.food_in_contact"></a>

#### food\_in\_contact

```python
def food_in_contact(creature: Creature) -> list[FoodResource]
```

All uneaten food within ``contact_radius`` of the creature.

Distances to every food are computed in one vectorized pass; only the
handful that fall inside the radius are then touched in Python.

<a id="rgb_evo_view.world.World.nearest_creature"></a>

#### nearest\_creature

```python
def nearest_creature(creature: Creature,
                     pool: list[Creature]) -> Creature | None
```

The creature in ``pool`` closest to ``creature`` by position (excluding itself).

<a id="rgb_evo_view.world.World.clear_food"></a>

#### clear\_food

```python
def clear_food() -> None
```

Remove all food (called when the walk phase ends).
