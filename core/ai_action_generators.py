"""
AI Action Generators - Convert batch AI decisions into interactive action queues.

These functions implement the strangler fig pattern by routing old batch AI
through the new interactive action system when interactive_ai_mode=True.
"""

from typing import Any
from core.actions.ai import (
    AIActionQueue,
    MerchantMoveAction,
    MerchantDamageCheckAction,
    EscortActivationAction,
    EscortMoveAction,
    EscortFireAction,
    EscortDepthChargeAction,
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
        # Damaged merchants need damage check first
        if merchant.damaged:
            queue.add(MerchantDamageCheckAction(
                entity_index=ship_idx,
                required_roll=4  # Standard damage check roll
            ))
        
        # Get next move from merchant AI
        target_hex, _new_facing, _message = game_state.merchant_ai.get_merchant_movement(
            merchant,
            ship_idx
        )
        
        if target_hex:
            queue.add(MerchantMoveAction(
                entity_index=ship_idx,
                target_hex=target_hex
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
    
    # Escort detection checks (one per active escort)
    escorts = [(i, ship) for i, ship in enumerate(game_state.ships)
               if ship.ship_type in ['corvette', 'destroyer']]
    
    for ship_idx, _escort in escorts:
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
    
    Creates basic escort actions - the action classes themselves handle
    the logic for determining targets and behavior.
    
    Args:
        game_state: Game state with ships, u_boat, escort_ai, etc.
    
    Returns:
        AIActionQueue with escort actions for player to execute
    """
    queue = AIActionQueue()
    
    # Find all escorts
    escorts = [(i, ship) for i, ship in enumerate(game_state.ships)
               if ship.ship_type in ['corvette', 'destroyer']]
    
    if not escorts:
        return queue
    
    # For each escort, create basic action sequence
    # The actions themselves will determine targets and behavior
    for ship_idx, escort in escorts:
        # 1. Activation check (escort die roll)
        queue.add(EscortActivationAction(
            entity_index=ship_idx,
            detection_level=game_state.detection_level
        ))
        
        # 2. Movement (action determines if it should move or turn)
        queue.add(EscortMoveAction(
            entity_index=ship_idx,
            target_hex=None  # Action calculates target
        ))
        
        # 3. Attack actions if in range
        distance = game_state.hex_grid.hex_distance(escort.position, game_state.u_boat.position)
        
        # Depth charge if adjacent
        if distance == 1:
            queue.add(EscortDepthChargeAction(
                entity_index=ship_idx,
                detection_level=game_state.detection_level
            ))
        
        # Gunfire if in range (2-3 hexes)
        if 2 <= distance <= 3:
            queue.add(EscortFireAction(
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
    
    # For each B-24, determine actions based on AI logic
    for aircraft_idx, aircraft in enumerate(game_state.aircraft):
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
