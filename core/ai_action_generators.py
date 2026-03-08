"""
AI Action Generators - Convert batch AI decisions into interactive action queues.

These functions implement the strangler fig pattern by routing old batch AI
through the new interactive action system when interactive_ai_mode=True.
"""

import random
from typing import Any
from core.actions.ai import (
    AIActionQueue,
    MerchantMoveAction,
    MerchantDamageCheckAction,
    EscortActivationAction,
    EscortDetectionAction,
    MerchantVisualAction,
    B24MoveAction,
    B24TurnAction,
    B24BombAction,
    FlakDefenseAction
)


def generate_merchant_actions(game_state: Any) -> AIActionQueue:
    """Generate interactive actions for merchant phase.
    
    Uses MerchantAI logic to determine moves, then creates interactive actions
    for player execution.
    
    Args:
        game_state: Game state with ships, merchant_ai, etc.
    
    Returns:
        AIActionQueue with merchant actions for player to execute
    """
    queue = AIActionQueue()
    
    # Find all merchants
    merchants = [(i, ship) for i, ship in enumerate(game_state.ships) 
                 if ship.ship_type == 'merchant']
    
    if not merchants:
        return queue
    
    # For each merchant, determine action based on AI logic
    for ship_idx, merchant in merchants:
        if merchant.damaged:
            # Damaged merchant: queue ONLY the damage check.
            # MerchantDamageCheckAction injects a MerchantMoveAction via
            # insert_after_current() if and only if the 4+ roll succeeds.
            queue.add(MerchantDamageCheckAction(
                entity_index=ship_idx,
                required_roll=4
            ))
        else:
            # Undamaged merchant: move directly.
            target_hex, new_facing, _message = game_state.merchant_ai.get_merchant_movement(
                merchant,
                ship_idx
            )
            if target_hex:
                queue.add(MerchantMoveAction(
                    entity_index=ship_idx,
                    target_hex=target_hex,
                    new_facing=new_facing
                ))
    
    return queue


def generate_detection_actions(game_state: Any) -> AIActionQueue:
    """Generate interactive actions for detection phase.
    
    Uses DetectionAI logic to determine detection checks, then creates
    interactive actions for player to roll dice.
    
    Args:
        game_state: Game state with ships, u_boat, detection_ai, etc.
    
    Returns:
        AIActionQueue with detection actions for player to execute
    """
    queue = AIActionQueue()
    
    # Skip detection if already at maximum
    if game_state.detection_level >= 3:
        return queue
    
    # Escort detection checks (one per active escort)
    escorts = [(i, ship) for i, ship in enumerate(game_state.ships)
               if ship.ship_type in ['corvette', 'destroyer']]
    
    detection_range = 3  # Rules: escorts may only detect within 3 hexes
    for ship_idx, escort in escorts:
        range_to_uboat = game_state.hex_grid.hex_distance(
            escort.position, game_state.u_boat.position
        )
        if range_to_uboat > detection_range:
            continue  # Escort out of detection range — skip
        queue.add(EscortDetectionAction(
            ship_index=ship_idx,
            current_detection_level=game_state.detection_level
        ))
    
    # Merchant visual sighting checks
    merchants = [(i, ship) for i, ship in enumerate(game_state.ships)
                 if ship.ship_type == 'merchant']
    
    for ship_idx, _merchant in merchants:
        queue.add(MerchantVisualAction(
            ship_index=ship_idx,
            current_detection_level=game_state.detection_level
        ))
    
    return queue


def generate_escort_actions(game_state: Any) -> AIActionQueue:
    """Generate interactive actions for escort phase.

    Escorts activate in order from closest to the U-boat (random shuffle resolves
    ties). For each escort, a single EscortActivationAction is queued; when the
    player rolls its dice, the action injects one EscortDieAction per die so the
    player resolves them individually (lowest die first).

    Args:
        game_state: Game state with ships, u_boat, escort_ai, etc.

    Returns:
        AIActionQueue with one EscortActivationAction per escort, ordered closest first.
    """
    queue = AIActionQueue()

    # Find all escorts
    escorts_raw = [(i, ship) for i, ship in enumerate(game_state.ships)
                   if ship.ship_type in ['corvette', 'destroyer']]

    if not escorts_raw:
        return queue

    # Compute distances and shuffle first for random tie-breaking, then stable-sort by distance
    escorts_with_dist = [
        (i, ship, game_state.hex_grid.hex_distance(ship.position, game_state.u_boat.position))
        for i, ship in escorts_raw
    ]
    random.shuffle(escorts_with_dist)
    escorts_with_dist.sort(key=lambda x: x[2])  # stable sort keeps ties in random order

    # Queue only the activation action — it dynamically injects EscortDieActions when rolled
    for ship_idx, _ship, _dist in escorts_with_dist:
        queue.add(EscortActivationAction(
            entity_index=ship_idx,
            detection_level=game_state.detection_level
        ))

    return queue


def generate_b24_actions(game_state: Any) -> AIActionQueue:
    """Generate interactive actions for B-24 phase.
    
    Uses B24AI logic to determine aircraft behaviors, then creates
    interactive actions for player to execute with dice.
    
    Args:
        game_state: Game state with aircraft, u_boat, b24_ai, etc.
    
    Returns:
        AIActionQueue with B-24 actions for player to execute
    """
    queue = AIActionQueue()
    
    if not game_state.aircraft:
        return queue
    
    # Process aircraft in REVERSE order (highest index first)
    # This ensures that if an aircraft is removed from the list, lower indices remain valid
    for aircraft_idx in range(len(game_state.aircraft) - 1, -1, -1):
        aircraft = game_state.aircraft[aircraft_idx]
        
        # 1. Movement (always moves forward)
        queue.add(B24MoveAction(aircraft_index=aircraft_idx))
        
        # 2. Turning (if not facing target)
        if not game_state.b24_ai._is_facing_target(
            aircraft.position,
            aircraft.facing,
            game_state.u_boat.position
        ):
            queue.add(B24TurnAction(
                aircraft_index=aircraft_idx,
                detection_level=game_state.detection_level
            ))
        
        # 3. Bombing attack (if over target)
        if aircraft.position == game_state.u_boat.position:
            queue.add(B24BombAction(
                aircraft_index=aircraft_idx
            ))
            
            # 4. Flak defense (if bombing)
            queue.add(FlakDefenseAction(
                aircraft_index=aircraft_idx
            ))
    
    return queue
