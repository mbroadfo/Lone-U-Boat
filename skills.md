# Type Hint Best Practices for Interactive AI Development

## Critical Type Annotation Patterns

### 1. Collection Types with getattr()
When using `getattr()` with set() or list() defaults, always add explicit type annotations:

```python
# CORRECT - Type annotated
land_hexes: set[HexCoord] = getattr(game_state.hex_grid, 'land_hexes', set())
shallow_hexes: set[HexCoord] = getattr(game_state.hex_grid, 'shallow_hexes', set())

# INCORRECT - Partially unknown type
land_hexes = getattr(game_state.hex_grid, 'land_hexes', set())
```

### 2. Fixture Parameters
All pytest fixture parameters must have type annotations:

```python
# CORRECT
@pytest.fixture
def simple_game_state(destroyer: Ship):
    class SimpleState:
        ships: list[Ship] = [destroyer]
    return SimpleState()

def test_something(simple_game_state: Any):
    pass

# INCORRECT - Missing annotations
def simple_game_state(destroyer):
    class SimpleState:
        ships = [destroyer]
    return SimpleState()
```

### 3. Import Management
- Remove ALL unused imports immediately after creating files
- Common unused imports: `Set` (use `set[T]` instead), `UBoat` in non-combat actions
- Always import `Any` from typing when using it in test fixtures

```python
# CORRECT imports for action files
from typing import Optional, Tuple
from core.models import Ship, HexCoord, Facing

# INCORRECT - includes unused Set
from typing import Optional, Tuple, Set
```

### 4. Test Variable Usage
Use `_` for validation returns that aren't checked:

```python
# CORRECT - unused reason
can_activate, _ = action.validate(game_state)

# INCORRECT - unused variable warning
can_activate, reason = action.validate(game_state)
```

### 5. Protected Attribute Access in Tests
Never directly access protected attributes (`_range`, `_has_los`, etc.) in tests:

```python
# CORRECT - use hasattr() or public interface
assert hasattr(action, '_range')
assert action.range <= 6  # If public property exists

# INCORRECT - protected access
assert action._range <= 6
```

### 6. Class Attributes
When defining class attributes, always include type annotations:

```python
# CORRECT
class MockGameState:
    land_hexes: set[HexCoord] = set()
    shallow_hexes: set[HexCoord] = set()
    ships: list[Ship] = []

# INCORRECT
class MockGameState:
    land_hexes = set()
    shallow_hexes = set()
```

### 7. Assertions Before Non-None Operations
Add assertions when type checker can't infer non-None:

```python
# CORRECT - assert before use
assert self.target_hex is not None
self.entity.position = self.target_hex

# May cause type checker warnings without assertion
self.entity.position = self.target_hex
```

## Development Workflow

1. **Before creating action file**: Plan which types will be needed
2. **While writing**: Add type annotations to ALL variables with collections
3. **After writing**: Remove unused imports
4. **Before tests**: Ensure fixtures have type annotations
5. **After initial test run**: Fix any type errors immediately
6. **Final check**: Run type checker before declaring completion

## Common Type Patterns for Actions

```python
# Action class property with type hints
@property
def entity_index(self) -> int:
    return self._entity_index

# Validation return with explicit types
def validate(self, game_state: Any) -> Tuple[bool, str]:
    land_hexes: set[HexCoord] = getattr(game_state.hex_grid, 'land_hexes', set())
    # ... validation logic
    return (True, "Validation passed")

# Execute with explicit return type
def execute(self, game_state: Any) -> ActionResult:
    return ActionResult(
        success=True,
        message="Action completed",
        ap_spent=0
    )
```

## Type Checking Verification

Always run these checks before completion:
1. `pytest run_tests.py -q` - All tests pass
2. Check for type errors in Problems panel
3. Verify 0 type errors in project files

## Why This Matters

Type errors break momentum and require multiple test-fix cycles. By following these patterns from the start:
- First test run is more likely to pass
- Type checker catches bugs early
- Code is more maintainable
- Development velocity stays high
