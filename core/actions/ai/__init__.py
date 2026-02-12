"""
Interactive AI Actions - Atomic AI behaviors for step-by-step gameplay.

This module provides action objects for AI entities (merchants, escorts, B-24s)
that can be executed one at a time with animations, allowing players to "roll
dice for the AI" just like in the physical board game.

This is a parallel implementation to the existing batch AI systems, enabled
via the `interactive_ai_mode` flag in Game initialization.
"""

from .base_ai_action import AIAction
from .merchant_move_action import MerchantMoveAction
from .merchant_damage_check_action import MerchantDamageCheckAction
from .escort_activation_action import EscortActivationAction
from .escort_die_action import EscortDieAction, EscortActionType
from .escort_move_action import EscortMoveAction
from .escort_turn_action import EscortTurnAction
from .escort_fire_action import EscortFireAction
from .escort_depth_charge_action import EscortDepthChargeAction
from .b24_move_action import B24MoveAction
from .b24_turn_action import B24TurnAction
from .b24_bomb_action import B24BombAction
from .flak_defense_action import FlakDefenseAction
from .escort_detection_action import EscortDetectionAction
from .merchant_visual_action import MerchantVisualAction
from .ai_action_queue import AIActionQueue

__all__ = [
    'AIAction',
    'MerchantMoveAction',
    'MerchantDamageCheckAction',
    'EscortActivationAction',
    'EscortDieAction',
    'EscortActionType',
    'EscortMoveAction',
    'EscortTurnAction',
    'EscortFireAction',
    'EscortDepthChargeAction',
    'B24MoveAction',
    'B24TurnAction',
    'B24BombAction',
    'FlakDefenseAction',
    'EscortDetectionAction',
    'MerchantVisualAction',
    'AIActionQueue',
]
