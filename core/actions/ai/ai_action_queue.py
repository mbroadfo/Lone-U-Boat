"""
AI Action Queue - Manages sequencing of player-executed AI actions.

During AI phases (Merchant, Escort, B-24, Detection), the game logic determines
what actions should happen, then presents them to the player for execution in
a solitaire-style gameplay experience.

This queue manages:
- Sequencing of AI actions during AI turns
- Presenting actions to player one at a time
- Collecting player inputs (dice rolls, confirmations)
- Executing actions and updating game state
"""

from typing import List, Optional, Any, Dict
from core.actions.ai.base_ai_action import AIAction
from core.actions.base_action import ActionResult


class AIActionQueue:
    """
    Queue for managing AI actions that the player executes.
    
    Unlike the player ActionQueue (which plans future actions), this queue
    contains actions determined by AI logic that the player must execute
    in sequence, one at a time (solitaire style).
    
    Example flow:
        # AI logic determines what should happen
        queue = AIActionQueue()
        queue.add(MerchantMoveAction(ship_index=0, ...))
        queue.add(EscortDetectionAction(ship_index=1, ...))
        
        # Player executes each action one at a time
        while not queue.is_empty():
            action = queue.current_action()
            preview = action.get_preview_data(game_state)
            # UI shows preview, player clicks "Execute"
            result = queue.execute_current(game_state)
            # UI shows result
            queue.next()
    """
    
    def __init__(self) -> None:
        """Initialize empty AI action queue."""
        self._actions: List[AIAction] = []
        self._current_index: int = 0
        self._execution_history: List[ActionResult] = []
    
    def add(self, action: AIAction) -> None:
        """
        Add an AI action to the queue.
        
        Args:
            action: AI action to add to queue
        """
        self._actions.append(action)
    
    def add_multiple(self, actions: List[AIAction]) -> None:
        """
        Add multiple AI actions to the queue at once.
        
        Args:
            actions: List of AI actions to add
        """
        self._actions.extend(actions)
    
    def current_action(self) -> Optional[AIAction]:
        """
        Get the current action to be executed.
        
        Returns:
            Current AI action, or None if queue is empty or all actions executed
        """
        if self._current_index < len(self._actions):
            return self._actions[self._current_index]
        return None
    
    def execute_current(self, game_state: Any) -> Optional[ActionResult]:
        """
        Execute the current action and return result.
        
        Does not advance the queue - call next() after showing result to player.
        
        Args:
            game_state: Current game state
            
        Returns:
            ActionResult from executing current action, or None if no current action
        """
        action = self.current_action()
        if action is None:
            return None
        
        # Check if action supports animation and has execute_with_animation method
        if (hasattr(action, 'triggers_animation') and action.triggers_animation and
            hasattr(action, 'execute_with_animation')):
            result = action.execute_with_animation(game_state)
        else:
            result = action.execute(game_state)
        
        self._execution_history.append(result)
        return result
    
    def insert_after_current(self, actions: List[AIAction]) -> None:
        """
        Insert actions immediately after the current position in the queue.
        
        Used by actions that dynamically determine follow-up work at execution
        time (e.g., EscortActivationAction injecting per-die EscortDieActions).
        
        Args:
            actions: List of actions to insert right after the current action
        """
        insert_pos = self._current_index + 1
        for i, action in enumerate(actions):
            self._actions.insert(insert_pos + i, action)

    def next(self) -> bool:
        """
        Move to next action in queue.
        
        Returns:
            True if there are more actions, False if queue exhausted
        """
        self._current_index += 1
        return self._current_index < len(self._actions)
    
    def is_empty(self) -> bool:
        """
        Check if queue has no actions.
        
        Returns:
            True if queue is empty
        """
        return len(self._actions) == 0
    
    def is_exhausted(self) -> bool:
        """
        Check if all actions have been executed.
        
        Returns:
            True if all actions in queue have been executed
        """
        return self._current_index >= len(self._actions)
    
    def remaining_count(self) -> int:
        """
        Get number of actions remaining (including current).
        
        Returns:
            Number of actions not yet executed
        """
        return max(0, len(self._actions) - self._current_index)
    
    def total_count(self) -> int:
        """
        Get total number of actions in queue.
        
        Returns:
            Total action count
        """
        return len(self._actions)
    
    def peek_next(self) -> Optional[AIAction]:
        """
        Preview the next action without advancing queue.
        
        Returns:
            Next action after current, or None if current is last
        """
        next_index = self._current_index + 1
        if next_index < len(self._actions):
            return self._actions[next_index]
        return None
    
    def get_all_actions(self) -> List[AIAction]:
        """
        Get all actions in queue (for debugging/display).
        
        Returns:
            List of all queued actions
        """
        return self._actions.copy()
    
    def get_execution_history(self) -> List[ActionResult]:
        """
        Get history of executed action results.
        
        Returns:
            List of ActionResults from executed actions
        """
        return self._execution_history.copy()
    
    def clear(self) -> None:
        """
        Clear all actions and reset queue.
        
        Used when starting a new AI phase or canceling current phase.
        """
        self._actions.clear()
        self._current_index = 0
        self._execution_history.clear()
    
    def reset_to_start(self) -> None:
        """
        Reset queue to beginning without clearing actions.
        
        Useful for replaying actions or debugging.
        """
        self._current_index = 0
        self._execution_history.clear()
    
    def get_progress(self) -> Dict[str, Any]:
        """
        Get progress information for UI display.
        
        Returns:
            Dictionary with progress stats:
            - current_index: Index of current action
            - total_count: Total actions in queue
            - remaining_count: Actions not yet executed
            - completed_count: Actions already executed
            - progress_percent: Percentage completed (0-100)
        """
        completed = self._current_index
        total = len(self._actions)
        remaining = max(0, total - completed)
        percent = int((completed / total * 100)) if total > 0 else 100
        
        return {
            'current_index': self._current_index,
            'total_count': total,
            'remaining_count': remaining,
            'completed_count': completed,
            'progress_percent': percent,
            'is_exhausted': self.is_exhausted(),
            'is_empty': self.is_empty()
        }
    
    def execute_all(self, game_state: Any) -> List[ActionResult]:
        """
        Execute all remaining actions in sequence (for automated testing).
        
        In normal gameplay, actions are executed one at a time with player
        interaction. This method is primarily for testing.
        
        Args:
            game_state: Current game state
            
        Returns:
            List of ActionResults from all executed actions
        """
        results: List[ActionResult] = []
        
        while not self.is_exhausted():
            result = self.execute_current(game_state)
            if result:
                results.append(result)
            self.next()
        
        return results
    
    def __len__(self) -> int:
        """
        Get queue length.
        
        Returns:
            Number of actions in queue
        """
        return len(self._actions)
    
    def __repr__(self) -> str:
        """
        Get string representation for debugging.
        
        Returns:
            Debug string showing queue state
        """
        return (
            f"AIActionQueue("
            f"total={len(self._actions)}, "
            f"current={self._current_index}, "
            f"remaining={self.remaining_count()})"
        )
