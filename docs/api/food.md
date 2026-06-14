<a id="rgb_evo_view.food"></a>

# rgb\_evo\_view.food

Food resources and how they are seeded each cycle.

Food is static -- once placed at the start of a cycle it never moves, and it
vanishes when eaten or when the cycle's walk phase ends.  Its ``genome`` (color)
decides which creatures can profitably eat it; its ``energy_value`` is the most
a perfectly matched creature could gain from it.

<a id="rgb_evo_view.food.FoodResource"></a>

## FoodResource Objects

```python
class FoodResource()
```

A single immovable morsel of food.

<a id="rgb_evo_view.food.spawn_food"></a>

#### spawn\_food

```python
def spawn_food(cfg: FoodConfig, world: World, rng: np.random.Generator,
               next_id: Callable[[], int]) -> list[FoodResource]
```

Create this cycle's food, scattered uniformly across the world.
