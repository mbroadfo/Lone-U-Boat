"""
AI U-Boat Captain for automated testing and gameplay.

Makes random tactical decisions to test game systems.
Uses ActionCatalog to query available actions from centralized rule logic.
"""

from typing import List, Tuple, Optional, Any, Dict
import random
from .models import UBoat, Ship, Depth, Facing
from .action_catalog import ActionCatalog
from .action_costs import ActionCostLookup
from .movement_validator import MovementValidator
from .depth_validator import DepthValidator
from .torpedo_validator import TorpedoValidator
from .repair_validator import RepairValidator
from .actions.base_action import ActionResult
from .damage.ship_damage import ShipDamageResolver


class UBoatAI:
    """AI controller for U-boat during testing/automated gameplay."""
    
    def __init__(self, game_state: Any):
        """
        Initialize AI captain.
        
        Args:
            game_state: Reference to main Game instance
        """
        self.game = game_state
        self.turn_count = 0
    
    def execute_turn(self) -> Tuple[bool, List[str]]:
        """
        Execute a full AI turn in Phase 1 (U-Boat Phase).
        
        Returns:
            Tuple of (success, messages)
        """
        messages: List[str] = []
        
        # Roll for AP if not already rolled
        if self.game.turn_manager.ap_tracker is None:
            ap = self.game.turn_manager.roll_action_points_only(self.game.u_boat)
            self.game.u_boat.action_points = ap
            self.game.action_queue.reset_for_new_turn(ap, self.game)
            messages.append(f"AI rolled {ap} AP")
        
        # Plan and queue actions
        actions_queued = self._plan_actions()
        messages.extend(actions_queued)
        
        # Commit all queued actions
        if self.game.action_queue.actions:
            results = self.game.action_queue.commit_all(self.game)
            for result in results:
                if result.success:
                    messages.append(f"[OK] {result.message}")
                    
                    # Check if action needs interactive combat resolution
                    if result.state_changes.get('needs_interactive_resolution'):
                        combat_messages = self._resolve_combat(result)
                        messages.extend(combat_messages)
                else:
                    messages.append(f"[FAIL] {result.message}")
            
            remaining = self.game.action_queue.get_remaining_ap(self.game)
            messages.append(f"Turn complete: {remaining} AP remaining")
        else:
            messages.append("No actions taken this turn")
        
        self.turn_count += 1
        return True, messages
    
    def _plan_actions(self) -> List[str]:
        """
        Plan and queue a set of random actions using ActionCatalog.
        
        Returns:
            List of messages about queued actions
        """
        messages: List[str] = []
        max_attempts = 50
        attempts = 0
        actions_added = 0
        
        # Try to use most of our AP (aim for 50%+ utilization)
        target_actions = max(3, self.game.action_queue.get_remaining_ap(self.game) // 2)
        
        # Create action cost lookup and validators
        cost_lookup = ActionCostLookup(self.game.mission_rules)
        movement_validator = MovementValidator(
            land_hexes=self.game.land_hexes,
            shallow_hexes=self.game.shallow_hexes,
            mission_hexes=self.game.mission_hexes
        )
        depth_validator = DepthValidator(shallow_hexes=self.game.shallow_hexes)
        torpedo_validator = TorpedoValidator()
        repair_validator = RepairValidator()
        
        # Create action catalog
        catalog = ActionCatalog(
            cost_lookup=cost_lookup,
            movement_validator=movement_validator,
            depth_validator=depth_validator,
            torpedo_validator=torpedo_validator,
            repair_validator=repair_validator,
            mission_rules=self.game.mission_rules,
            land_hexes=self.game.land_hexes,
            shallow_hexes=self.game.shallow_hexes,
            hex_grid=self.game.hex_grid,
            dice_roller=self.game.turn_manager.dice,
            mission_hexes=self.game.mission_hexes
        )
        
        # Keep trying to add actions until we can't afford any more
        while attempts < max_attempts and actions_added < target_actions:
            attempts += 1
            
            # Get remaining AP
            remaining_ap = self.game.action_queue.get_remaining_ap(self.game)
            if remaining_ap <= 0:
                break
            
            # Get all available actions from catalog
            available_actions = catalog.get_available_actions(self.game)
            
            if not available_actions:
                # No valid actions available
                continue
            
            # Randomly choose one available action
            chosen = random.choice(available_actions)
            
            # Try to add it to queue
            success, message = self.game.action_queue.add_action(chosen.action, self.game)
            if success:
                actions_added += 1
            else:
                # Action failed, try a different one
                continue
        
        return messages
    
    def _resolve_combat(self, action_result: ActionResult) -> List[str]:
        """
        Automatically resolve combat (torpedoes or deck gun).
        
        Args:
            action_result: The ActionResult with combat targets
            
        Returns:
            List of combat resolution messages
        """
        messages: List[str] = []
        action_name = action_result.state_changes.get('action_name', '')
        
        if action_name == "Fire Torpedo":
            messages.extend(self._resolve_torpedo_combat(action_result))
        elif action_name == "Fire Deck Gun":
            messages.extend(self._resolve_deck_gun_combat(action_result))
        
        return messages
    
    def _resolve_torpedo_combat(self, action_result: ActionResult) -> List[str]:
        """
        Resolve torpedo attack automatically.
        
        Args:
            action_result: The torpedo action result with targets
            
        Returns:
            List of messages about torpedo hits/misses
        """
        messages: List[str] = []
        targets = action_result.state_changes.get('targets', [])
        torpedo_count = action_result.state_changes.get('torpedo_count', 1)
        
        if not targets:
            messages.append("[COMBAT] Torpedoes missed - no targets in path")
            return messages
        
        # Get combat resolver
        combat_resolver = self.game.combat_resolver
        ship_damage = ShipDamageResolver(self.game.turn_manager.dice)
        
        total_hits = 0
        dl_increase = 0
        
        for ship, distance, aspect in targets:
            # Roll for torpedoes against this ship
            result = combat_resolver.resolve_torpedo_attack(
                range_to_target=distance,
                aspect=aspect,
                num_torpedoes=torpedo_count
            )
            
            if result['hits'] > 0:
                total_hits += result['hits']

                # Apply damage for each hit
                for i in range(result['hits']):
                    damage_result = ship_damage.apply_damage(ship=ship, weapon_type='torpedo')

                    messages.append(
                        f"[COMBAT] Torpedo #{i+1} HIT {ship.ship_type} at range {distance} ({aspect}): "
                        f"Roll {damage_result.roll} - {damage_result.description}"
                    )

                    if damage_result.is_now_sunk:
                        messages.append(f"[DAMAGE] {ship.ship_type} SUNK")
                
                # Track DL increase (+1 per hit, max +2)
                dl_increase = min(dl_increase + result['hits'], 2)
            else:
                messages.append(
                    f"[COMBAT] Torpedo MISS {ship.ship_type} at range {distance} ({aspect}): "
                    f"Rolled {result['rolls']} (need {result['target']}+)"
                )
        
        # Apply detection level increase
        if dl_increase > 0:
            old_dl = self.game.detection_level
            self.game.detection_level = min(3, old_dl + dl_increase)
            messages.append(f"[DL] Torpedo attack: DL {old_dl} -> {self.game.detection_level} (+{dl_increase})")
        
        return messages
    
    def _resolve_deck_gun_combat(self, action_result: ActionResult) -> List[str]:
        """
        Resolve deck gun attack automatically.
        
        Args:
            action_result: The deck gun action result with target
            
        Returns:
            List of messages about deck gun hit/miss
        """
        messages: List[str] = []
        target_ship = action_result.state_changes.get('target_ship')
        range_to_target = action_result.state_changes.get('range', 0)
        
        if not target_ship:
            messages.append("[COMBAT] Deck gun fired but no target")
            return messages
        
        # Get combat resolver
        combat_resolver = self.game.combat_resolver
        ship_damage = ShipDamageResolver(self.game.turn_manager.dice)
        
        # Roll to hit
        hit, roll_result, desc = combat_resolver.resolve_deck_gun_attack(range_to_target)
        
        if hit:
            damage_result = ship_damage.apply_damage(ship=target_ship, weapon_type='deck_gun')

            messages.append(
                f"[COMBAT] Deck Gun HIT {target_ship.ship_type} at range {range_to_target}: "
                f"2d6={roll_result}, Damage={damage_result.roll} - {damage_result.description}"
            )

            if damage_result.is_now_sunk:
                messages.append(f"[DAMAGE] {target_ship.ship_type} SUNK")
            
            # DL increases by 1 on hit
            old_dl = self.game.detection_level
            self.game.detection_level = min(3, old_dl + 1)
            messages.append(f"[DL] Deck gun hit: DL {old_dl} -> {self.game.detection_level} (+1)")
        else:
            messages.append(
                f"[COMBAT] Deck Gun MISS {target_ship.ship_type} at range {range_to_target}: "
                f"2d6={roll_result} (need {7 if range_to_target <= 2 else 8}+)"
            )
        
        return messages
