"""Damage resolution module for Lone U-Boat."""

from .ship_damage import ShipDamageResolver, ShipDamageResult
from .uboat_damage import UBoatDamageResolver, UBoatDamageResult

__all__ = [
    'ShipDamageResolver',
    'ShipDamageResult',
    'UBoatDamageResolver',
    'UBoatDamageResult'
]
