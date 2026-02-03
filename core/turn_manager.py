"""
Turn and phase management for Lone U-Boat.

Handles:
- Turn sequencing and phase transitions
- Action Point (AP) rolling and tracking
- Phase-specific logic execution
"""

from typing import List, Tuple, Optional, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass

from .models import GamePhase, UBoat, Depth
from .dice import DiceRoller

if TYPE_CHECKING:
    from .actions.action_history import ActionHistory


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
        self.remaining_ap: int = 0  # Track remaining AP for immediate execution
        self.action_history: Optional['ActionHistory'] = None  # Will be set by GameState
        self.phase_logs: Dict[str, List[str]] = {}
        self.depth_changed_this_turn: bool = False
        self.forced_dive_penalty: int = 0  # -2 AP if forced to dive
        
        # Dice roller for all random events
        self.dice = dice_roller if dice_roller else DiceRoller()
        
        # Store last AP roll details for UI display
        self.last_ap_roll: Optional[Dict[str, Any]] = None
        
        # Load AP rolling rules from JSON
        self.normal_dice_count: int = 3
        self.damaged_dice_count: int = 2
        self.captain_bonus: int = 1
        self._load_ap_rules()
        # Store last AP roll details for UI display
        self.last_ap_roll: Optional[Dict[str, Any]] = None
        
        # Load AP rolling rules from JSON
        self.normal_dice_count: int = 3
        self.damaged_dice_count: int = 2
        self.captain_bonus: int = 1
        self._load_ap_rules()
    
    def _load_ap_rules(self) -> None:
        """Load AP rolling rules from mission_rules JSON."""
        try:
            # Get u_boat_ap_rules section
            ap_rules = self.mission_rules.get_section_by_id("u_boat_ap_rules")
            
            if not ap_rules:
                return
            
            # Parse dice counts
            if "dice" in ap_rules:
                dice_config = ap_rules["dice"]
                # Parse "3d6" to extract dice count
                if "normal" in dice_config:
                    normal_str = dice_config["normal"]
                    if "d6" in normal_str:
                        self.normal_dice_count = int(normal_str.split("d")[0])
                
                if "damaged" in dice_config:
                    damaged_str = dice_config["damaged"]
                    if "d6" in damaged_str:
                        self.damaged_dice_count = int(damaged_str.split("d")[0])
            
            # Parse captain bonus from modifiers
            if "modifiers" in ap_rules:
                for modifier in ap_rules["modifiers"]:
                    if modifier.get("condition") == "captain_alive":
                        effect_str = modifier.get("effect", "+1 AP")
                        # Extract number from "+1 AP" format
                        if "+" in effect_str:
                            bonus_str = effect_str.split("+")[1].split()[0]
                            self.captain_bonus = int(bonus_str)
        
        except Exception:
            # Keep defaults if parsing fails
            pass
    
    def roll_action_points_only(self, u_boat: UBoat) -> int:
        """
        Roll for action points without advancing turn number.
        Used for initial turn setup when player clicks "Roll for AP".
        
        Args:
            u_boat: The player's U-boat
            
        Returns:
            Total action points for this turn
        """
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
        self.remaining_ap = ap  # Track remaining AP for immediate execution
        
        # Don't add phase log here - AP roll already shown at turn start
        
        return ap
    
    def start_new_turn(self, u_boat: UBoat) -> int:
        """
        Start a new turn, rolling AP and applying modifiers.
        This increments the turn number and should only be called when wrapping from END_TURN_PHASE.
        
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
        self.remaining_ap = ap  # Track remaining AP for immediate execution
        
        # Don't add phase log here - AP roll already shown at turn start
        
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
        # Determine number of dice (loaded from JSON)
        num_dice = self.damaged_dice_count if u_boat.engine_damaged else self.normal_dice_count
        
        # Roll dice using DiceRoller
        context = "Action Points (Engine damaged)" if u_boat.engine_damaged else "Action Points"
        highest, rolls = self.dice.roll_highest(num_dice, sides=6, context=context)
        
        # Calculate AP (captain bonus loaded from JSON)
        base_ap = highest
        captain_bonus = self.captain_bonus if u_boat.captain_alive else 0
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
        
        # Don't add phase logs here - AP roll is already announced at turn start
        
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
            print(f"[DL] Depth modifier at turn start: {depth.name} depth, DL {detection_level} -> {new_dl} ({modifier:+d})")
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
        
        # Clear AP state when entering new U-Boat phase (before dice roll)
        if turn_wrapped:
            self.last_ap_roll = None
            self.remaining_ap = 0
        
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
            GamePhase.END_TURN_EVENTS: "End Turn Events",
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
    
    def clear_action_history(self):
        """Clear action history when phase advances (can't undo across phases)."""
        if self.action_history is not None:
            self.action_history.clear()
    
    def execute_action_immediate(self, ap_cost: int) -> bool:
        """
        Execute action immediately and deduct AP.
        
        Args:
            ap_cost: AP cost of the action
            
        Returns:
            True if sufficient AP available, False otherwise
        """
        if self.remaining_ap >= ap_cost:
            self.remaining_ap -= ap_cost
            return True
        return False
