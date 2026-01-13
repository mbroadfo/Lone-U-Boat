"""
Turn and phase management for Lone U-Boat.

Handles:
- Turn sequencing and phase transitions
- Action Point (AP) rolling and tracking
- Phase-specific logic execution
"""

from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

from .models import GamePhase, UBoat, Depth
from .dice import DiceRoller


@dataclass
class ActionRecord:
    """Record of an action taken during a turn."""
    action_name: str
    ap_cost: int
    details: str = ""


class ActionPointTracker:
    """Tracks and validates AP spending during U-Boat phase."""
    
    def __init__(self, initial_ap: int):
        """
        Initialize AP tracker.
        
        Args:
            initial_ap: Starting action points for this turn
        """
        self.total_ap: int = initial_ap
        self.spent_ap: int = 0
        self.action_history: List[ActionRecord] = []
    
    def can_afford(self, action: str, cost: int) -> bool:
        """
        Check if enough AP remains for action.
        
        Args:
            action: Name of action to perform
            cost: AP cost of action
            
        Returns:
            True if sufficient AP available
        """
        return self.remaining() >= cost
    
    def spend(self, action: str, cost: int, details: str = "") -> bool:
        """
        Spend AP on action.
        
        Args:
            action: Name of action performed
            cost: AP cost of action
            details: Optional description of action result
            
        Returns:
            True if action was successfully charged, False if insufficient AP
        """
        if not self.can_afford(action, cost):
            return False
        
        self.spent_ap += cost
        self.action_history.append(ActionRecord(action, cost, details))
        return True
    
    def remaining(self) -> int:
        """Get remaining unspent AP."""
        return self.total_ap - self.spent_ap
    
    def reset(self, new_ap: int):
        """
        Reset for new turn.
        
        Args:
            new_ap: Action points for next turn
        """
        self.total_ap = new_ap
        self.spent_ap = 0
        self.action_history.clear()
    
    def get_history_summary(self) -> List[str]:
        """Get formatted action history for display."""
        summary: List[str] = []
        for record in self.action_history:
            line = f"{record.action_name} ({record.ap_cost} AP)"
            if record.details:
                line += f" - {record.details}"
            summary.append(line)
        return summary


class TurnManager:
    """Manages game turns and phase transitions."""
    
    # Phase order definition
    PHASE_ORDER = [
        GamePhase.UBOAT_PHASE,
        GamePhase.MERCHANT_PHASE,
        GamePhase.DETECTION_PHASE,
        GamePhase.ESCORT_PHASE,
        GamePhase.B24_PHASE,
        GamePhase.END_TURN_EVENTS,
        GamePhase.END_TURN_PHASE,
    ]
    
    def __init__(self, mission_rules: Any, dice_roller: Optional[DiceRoller] = None):
        """
        Initialize turn manager.
        
        Args:
            mission_rules: MissionRules instance with JSON rule data
            dice_roller: Optional DiceRoller instance (creates new if None)
        """
        self.mission_rules = mission_rules
        self.turn_number: int = 1
        self.current_phase: GamePhase = GamePhase.UBOAT_PHASE
        self.ap_tracker: Optional[ActionPointTracker] = None
        self.phase_logs: Dict[str, List[str]] = {}
        self.depth_changed_this_turn: bool = False
        self.forced_dive_penalty: int = 0  # -2 AP if forced to dive
        
        # Dice roller for all random events
        self.dice = dice_roller if dice_roller else DiceRoller()
        
        # Store last AP roll details for UI display
        self.last_ap_roll: Optional[Dict[str, Any]] = None
    
    def start_new_turn(self, u_boat: UBoat) -> int:
        """
        Start a new turn, rolling AP and applying modifiers.
        
        Args:
            u_boat: The player's U-boat
            
        Returns:
            Total action points for this turn
        """
        self.turn_number += 1
        self.current_phase = GamePhase.UBOAT_PHASE
        self.phase_logs.clear()
        self.depth_changed_this_turn = False
        
        # Roll for Action Points
        ap = self._roll_action_points(u_boat)
        
        # Apply forced dive penalty if applicable
        if self.forced_dive_penalty > 0:
            ap = max(0, ap - self.forced_dive_penalty)
            self.add_phase_log("U-Boat Phase", 
                             f"Forced dive penalty: -{self.forced_dive_penalty} AP")
            self.forced_dive_penalty = 0
        
        # Initialize AP tracker
        self.ap_tracker = ActionPointTracker(ap)
        
        self.add_phase_log("U-Boat Phase", 
                         f"Turn {self.turn_number} started with {ap} AP")
        
        return ap
    
    def _roll_action_points(self, u_boat: UBoat) -> int:
        """
        Roll for action points based on U-boat state.
        
        Rules from u_boat_ruleset_default.json:
        - Roll 3d6 (or 2d6 if engine damaged)
        - Take highest die
        - Add +1 if captain alive
        
        Args:
            u_boat: The player's U-boat
            
        Returns:
            Total action points
        """
        # Determine number of dice
        num_dice = 2 if u_boat.engine_damaged else 3
        
        # Roll dice using DiceRoller
        context = "Action Points (Engine damaged)" if u_boat.engine_damaged else "Action Points"
        highest, rolls = self.dice.roll_highest(num_dice, sides=6, context=context)
        
        # Calculate AP
        base_ap = highest
        captain_bonus = 1 if u_boat.captain_alive else 0
        ap = base_ap + captain_bonus
        
        # Store detailed roll info for UI display
        self.last_ap_roll = {
            'num_dice': num_dice,
            'rolls': rolls,
            'highest': highest,
            'captain_bonus': captain_bonus,
            'total_ap': ap,
            'engine_damaged': u_boat.engine_damaged
        }
        
        # Log the roll
        roll_str = ", ".join(str(r) for r in rolls)
        self.add_phase_log("U-Boat Phase", 
                         f"AP Roll: [{roll_str}] → Highest: {highest}")
        if u_boat.captain_alive:
            self.add_phase_log("U-Boat Phase", "Captain bonus: +1 AP")
        
        return ap
    
    def apply_depth_detection_modifier(self, detection_level: int, depth: Depth) -> int:
        """
        Apply detection level modifier based on depth at turn start.
        
        Rules from u_boat_ruleset_default.json:
        - Medium depth: -1 DL
        - Deep: -2 DL
        - Cannot go below 0
        
        Args:
            detection_level: Current detection level (0-3)
            depth: U-boat's current depth
            
        Returns:
            New detection level
        """
        modifier = 0
        
        if depth == Depth.MEDIUM:
            modifier = -1
        elif depth == Depth.DEEP:
            modifier = -2
        
        new_dl = max(0, detection_level + modifier)
        
        if modifier < 0:
            self.add_phase_log("U-Boat Phase",
                             f"Depth modifier: {modifier} DL (now DL {new_dl})")
        
        return new_dl
    
    def advance_phase(self) -> Tuple[GamePhase, bool]:
        """
        Move to next phase in sequence.
        
        Returns:
            (new_phase, turn_wrapped)
            turn_wrapped is True if we completed END_TURN_PHASE and wrapped to next turn
        """
        current_index = self.PHASE_ORDER.index(self.current_phase)
        next_index = (current_index + 1) % len(self.PHASE_ORDER)
        
        self.current_phase = self.PHASE_ORDER[next_index]
        
        # Check if we wrapped back to U-Boat Phase (new turn)
        turn_wrapped = (next_index == 0)
        
        return self.current_phase, turn_wrapped
    
    def can_advance_phase(self, u_boat: Optional[UBoat] = None) -> Tuple[bool, str]:
        """
        Check if current phase can advance.
        
        Args:
            u_boat: Optional U-boat for phase-specific checks
            
        Returns:
            (can_advance, reason_if_not)
        """
        # Most phases can always advance (player presses SPACE when ready)
        # Future: Could add validation like "merchant must move before advancing"
        
        if self.current_phase == GamePhase.UBOAT_PHASE:
            # Player can advance whenever (even with AP remaining)
            return True, ""
        
        return True, ""
    
    def add_phase_log(self, phase_name: str, message: str):
        """
        Add a log entry for a phase.
        
        Args:
            phase_name: Name of phase (e.g., "Merchant Phase")
            message: Log message
        """
        if phase_name not in self.phase_logs:
            self.phase_logs[phase_name] = []
        self.phase_logs[phase_name].append(message)
    
    def get_phase_log(self, phase_name: str) -> List[str]:
        """Get log entries for a specific phase."""
        return self.phase_logs.get(phase_name, [])
    
    def get_current_phase_name(self) -> str:
        """Get display name for current phase."""
        phase_names = {
            GamePhase.UBOAT_PHASE: "U-Boat Phase",
            GamePhase.MERCHANT_PHASE: "Merchant Phase",
            GamePhase.DETECTION_PHASE: "Detection Phase",
            GamePhase.ESCORT_PHASE: "Escort Phase",
            GamePhase.B24_PHASE: "B24 Aircraft Phase",
            GamePhase.END_TURN_PHASE: "End Turn Phase",
        }
        return phase_names.get(self.current_phase, "Unknown Phase")
    
    def mark_depth_changed(self):
        """Mark that depth change action was used this turn (once per turn limit)."""
        self.depth_changed_this_turn = True
    
    def can_change_depth(self) -> bool:
        """Check if depth can be changed (once per turn rule)."""
        return not self.depth_changed_this_turn
    
    def set_forced_dive_penalty(self):
        """Set forced dive penalty for next turn (-2 AP)."""
        self.forced_dive_penalty = 2
