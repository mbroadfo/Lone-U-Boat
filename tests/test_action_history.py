"""
Tests for ActionHistory - immediate execution with single-level undo.

Tests verify:
- Recording actions with state snapshots
- Undo retrieves correct state
- Can only undo most recent action
- Clear removes undo capability
- Helper functions for U-boat state snapshots
"""

import pytest
from core.actions.action_history import (
    ActionHistory,
    create_u_boat_snapshot,
    restore_u_boat_snapshot
)
from core.actions.fire_torpedo_action import FireTorpedoAction
from core.actions.load_torpedo_action import LoadTorpedoAction
from core.models import UBoat, HexCoord, Facing, Depth, TubeState


class TestActionHistory:
    """Test ActionHistory functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test."""
        self.history = ActionHistory()
        self.u_boat = UBoat(
            position=HexCoord(5, 5),
            facing=Facing.NORTH,
            depth=Depth.SURFACED
        )
    
    def test_initial_state(self):
        """Test that new ActionHistory has no undo available."""
        assert not self.history.can_undo(), "New history should have no undo"
        assert self.history.get_undo_action_name() == "", "No action name when empty"
        assert self.history.get_last_action_cost() == 0, "No cost when empty"
    
    def test_record_action(self):
        """Test recording an action makes it available for undo."""
        # Create mock action
        action = FireTorpedoAction(
            tube_indices=[1],
            fire_direction=Facing.NORTH,
            cost_lookup=None,
            validator=None,
            los_calculator=None,
            combat_resolver=None
        )
        
        # Record action
        snapshot = {
            'u_boat_state': create_u_boat_snapshot(self.u_boat),
            'remaining_ap': 7
        }
        self.history.record_action(action, ap_cost=2, state_snapshot=snapshot)
        
        # Verify undo available
        assert self.history.can_undo(), "Should have undo available after recording"
        assert "FireTorpedoAction" in self.history.get_undo_action_name(), \
            "Should show fire torpedo action name"
        assert self.history.get_last_action_cost() == 2, "Should track AP cost"
    
    def test_undo_returns_snapshot(self):
        """Test that undo returns the recorded state snapshot."""
        # Record action with snapshot
        original_snapshot = {
            'u_boat_state': create_u_boat_snapshot(self.u_boat),
            'remaining_ap': 5
        }
        action = LoadTorpedoAction(
            tube_indices=[1, 2],
            cost_lookup=None,
            validator=None
        )
        self.history.record_action(action, ap_cost=1, state_snapshot=original_snapshot)
        
        # Perform undo
        restored = self.history.undo_last_action()
        
        # Verify snapshot returned
        assert restored is not None, "Undo should return snapshot"
        assert restored['remaining_ap'] == 5, "Should restore AP"
        assert restored['ap_refund'] == 1, "Should include AP refund"
        assert 'u_boat_state' in restored, "Should include U-boat state"
    
    def test_undo_clears_history(self):
        """Test that undo clears history (can't undo twice)."""
        # Record and undo
        snapshot = {'remaining_ap': 7}
        action = LoadTorpedoAction(tube_indices=[1], cost_lookup=None, validator=None)
        self.history.record_action(action, ap_cost=1, state_snapshot=snapshot)
        
        first_undo = self.history.undo_last_action()
        assert first_undo is not None, "First undo should work"
        
        # Try to undo again
        second_undo = self.history.undo_last_action()
        assert second_undo is None, "Second undo should return None"
        assert not self.history.can_undo(), "Should not have undo after undo"
    
    def test_clear_removes_undo(self):
        """Test that clear() removes undo capability."""
        # Record action
        snapshot = {'remaining_ap': 6}
        action = LoadTorpedoAction(tube_indices=[1], cost_lookup=None, validator=None)
        self.history.record_action(action, ap_cost=1, state_snapshot=snapshot)
        
        assert self.history.can_undo(), "Should have undo before clear"
        
        # Clear history
        self.history.clear()
        
        assert not self.history.can_undo(), "Should not have undo after clear"
        assert self.history.get_undo_action_name() == "", "Action name cleared"
        assert self.history.get_last_action_cost() == 0, "Cost cleared"
    
    def test_recording_new_action_replaces_old(self):
        """Test that recording new action replaces previous undo."""
        # Record first action
        action1 = LoadTorpedoAction(tube_indices=[1], cost_lookup=None, validator=None)
        snapshot1 = {'remaining_ap': 7}
        self.history.record_action(action1, ap_cost=1, state_snapshot=snapshot1)
        
        # Record second action
        action2 = FireTorpedoAction(
            tube_indices=[1],
            fire_direction=Facing.NORTH,
            cost_lookup=None,
            validator=None,
            los_calculator=None,
            combat_resolver=None
        )
        snapshot2 = {'remaining_ap': 6}
        self.history.record_action(action2, ap_cost=2, state_snapshot=snapshot2)
        
        # Undo should restore second action only
        assert "FireTorpedoAction" in self.history.get_undo_action_name(), \
            "Should show most recent action"
        
        restored = self.history.undo_last_action()
        assert restored['remaining_ap'] == 6, "Should restore second action's AP"
        assert restored['ap_refund'] == 2, "Should refund second action's cost"
    
    def test_undo_when_no_action_recorded(self):
        """Test that undo returns None when no action recorded."""
        result = self.history.undo_last_action()
        assert result is None, "Undo with no action should return None"


class TestUBoatSnapshot:
    """Test U-boat state snapshot helpers."""
    
    def setup_method(self):
        """Set up test fixtures before each test."""
        self.u_boat = UBoat(
            position=HexCoord(5, 5),
            facing=Facing.NORTH,
            depth=Depth.SURFACED
        )
    
    def test_create_snapshot(self):
        """Test creating U-boat state snapshot."""
        # Modify state
        self.u_boat.torpedo_tubes[0] = TubeState.EMPTY
        self.u_boat.torpedo_tubes[1] = TubeState.DAMAGED
        self.u_boat.engine_damaged = True
        self.u_boat.hull_damage = 3
        
        # Create snapshot
        snapshot = create_u_boat_snapshot(self.u_boat)
        
        # Verify all fields captured
        assert snapshot['position'] == (5, 5), "Position captured"
        assert snapshot['facing'] == Facing.NORTH.value, "Facing captured"
        assert snapshot['depth'] == Depth.SURFACED.value, "Depth captured"
        assert snapshot['torpedo_tubes'][0] == TubeState.EMPTY.value, "Tube 1 empty"
        assert snapshot['torpedo_tubes'][1] == TubeState.DAMAGED.value, "Tube 2 damaged"
        assert snapshot['engine_damaged'] == True, "Engine damage captured"
        assert snapshot['hull_damage'] == 3, "Hull damage captured"
    
    def test_restore_snapshot(self):
        """Test restoring U-boat state from snapshot."""
        # Create initial snapshot
        original_snapshot = create_u_boat_snapshot(self.u_boat)
        
        # Modify U-boat state
        self.u_boat.position = HexCoord(10, 10)
        self.u_boat.facing = Facing.SOUTH
        self.u_boat.depth = Depth.DEEP
        self.u_boat.torpedo_tubes[0] = TubeState.EMPTY
        self.u_boat.deck_gun_damaged = True
        self.u_boat.hull_damage = 5
        
        # Restore from snapshot
        restore_u_boat_snapshot(self.u_boat, original_snapshot)
        
        # Verify restoration
        assert self.u_boat.position == HexCoord(5, 5), "Position restored"
        assert self.u_boat.facing == Facing.NORTH, "Facing restored"
        assert self.u_boat.depth == Depth.SURFACED, "Depth restored"
        assert self.u_boat.torpedo_tubes[0] == TubeState.LOADED, "Tube 1 restored to loaded"
        assert self.u_boat.deck_gun_damaged == False, "Deck gun not damaged after restore"
        assert self.u_boat.hull_damage == 0, "Hull damage restored to 0"
    
    def test_snapshot_independence(self):
        """Test that snapshot is independent of original state."""
        # Create snapshot
        snapshot = create_u_boat_snapshot(self.u_boat)
        
        # Modify original
        self.u_boat.torpedo_tubes[0] = TubeState.EMPTY
        self.u_boat.hull_damage = 10
        
        # Verify snapshot unchanged
        assert snapshot['torpedo_tubes'][0] == TubeState.LOADED.value, \
            "Snapshot tube should still be loaded"
        assert snapshot['hull_damage'] == 0, "Snapshot hull damage should be 0"
    
    def test_round_trip_snapshot_restore(self):
        """Test that snapshot → modify → restore returns to original state."""
        # Set complex initial state
        self.u_boat.position = HexCoord(3, 7)
        self.u_boat.facing = Facing.SOUTHWEST
        self.u_boat.depth = Depth.PERISCOPE
        self.u_boat.torpedo_tubes = [
            TubeState.LOADED,
            TubeState.EMPTY,
            TubeState.DAMAGED,
            TubeState.LOADED,
            TubeState.EMPTY
        ]
        self.u_boat.engine_damaged = True
        self.u_boat.deck_gun_damaged = True
        self.u_boat.hull_damage = 2
        
        # Snapshot original state
        snapshot = create_u_boat_snapshot(self.u_boat)
        
        # Make drastic changes
        self.u_boat.position = HexCoord(99, 99)
        self.u_boat.facing = Facing.NORTH
        self.u_boat.depth = Depth.DEEP
        self.u_boat.torpedo_tubes = [TubeState.EMPTY] * 5
        self.u_boat.engine_damaged = False
        self.u_boat.deck_gun_damaged = False
        self.u_boat.hull_damage = 0
        
        # Restore
        restore_u_boat_snapshot(self.u_boat, snapshot)
        
        # Verify exact restoration
        assert self.u_boat.position == HexCoord(3, 7), "Position restored exactly"
        assert self.u_boat.facing == Facing.SOUTHWEST, "Facing restored exactly"
        assert self.u_boat.depth == Depth.PERISCOPE, "Depth restored exactly"
        assert self.u_boat.torpedo_tubes[0] == TubeState.LOADED, "Tube 1 restored"
        assert self.u_boat.torpedo_tubes[1] == TubeState.EMPTY, "Tube 2 restored"
        assert self.u_boat.torpedo_tubes[2] == TubeState.DAMAGED, "Tube 3 restored"
        assert self.u_boat.torpedo_tubes[3] == TubeState.LOADED, "Tube 4 restored"
        assert self.u_boat.torpedo_tubes[4] == TubeState.EMPTY, "Tube 5 restored"
        assert self.u_boat.engine_damaged == True, "Engine damage restored"
        assert self.u_boat.deck_gun_damaged == True, "Deck gun damage restored"
        assert self.u_boat.hull_damage == 2, "Hull damage restored exactly"


class TestActionHistoryIntegration:
    """Integration tests for ActionHistory with game flow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.history = ActionHistory()
        self.u_boat = UBoat(
            position=HexCoord(5, 5),
            facing=Facing.NORTH,
            depth=Depth.SURFACED
        )
    
    def test_typical_action_undo_flow(self):
        """Test typical flow: execute action → undo → state restored."""
        # Initial state
        initial_ap = 7
        self.u_boat.torpedo_tubes[0] = TubeState.LOADED
        
        # Create snapshot before action
        snapshot = {
            'u_boat_state': create_u_boat_snapshot(self.u_boat),
            'remaining_ap': initial_ap
        }
        
        # Simulate executing action (fire torpedo)
        action = FireTorpedoAction(
            tube_indices=[1],
            fire_direction=Facing.NORTH,
            cost_lookup=None,
            validator=None,
            los_calculator=None,
            combat_resolver=None
        )
        self.history.record_action(action, ap_cost=2, state_snapshot=snapshot)
        
        # Simulate action effect (tube now empty)
        self.u_boat.torpedo_tubes[0] = TubeState.EMPTY
        ap_after_action = 5
        
        # Player clicks undo
        restored = self.history.undo_last_action()
        assert restored is not None, "Undo should return snapshot"
        
        # Restore state
        restore_u_boat_snapshot(self.u_boat, restored['u_boat_state'])
        restored_ap = restored['remaining_ap']
        
        # Verify restoration
        assert self.u_boat.torpedo_tubes[0] == TubeState.LOADED, "Tube restored to loaded"
        assert restored_ap == 7, "AP restored to pre-action value"
        assert restored['ap_refund'] == 2, "AP refund is action cost"
    
    def test_phase_advance_clears_history(self):
        """Test that advancing phase clears undo (can't undo across phases)."""
        # Record action
        snapshot = {'remaining_ap': 5}
        action = LoadTorpedoAction(tube_indices=[1], cost_lookup=None, validator=None)
        self.history.record_action(action, ap_cost=1, state_snapshot=snapshot)
        
        assert self.history.can_undo(), "Should have undo in same phase"
        
        # Simulate phase advance
        self.history.clear()
        
        assert not self.history.can_undo(), "Should not have undo after phase advance"
    
    def test_multiple_actions_only_last_undoable(self):
        """Test that only the most recent action can be undone."""
        # Execute 3 actions
        for i in range(3):
            snapshot = {'remaining_ap': 7 - i, 'action_num': i}
            action = LoadTorpedoAction(tube_indices=[i+1], cost_lookup=None, validator=None)
            self.history.record_action(action, ap_cost=1, state_snapshot=snapshot)
        
        # Only last action (i=2) should be undoable
        restored = self.history.undo_last_action()
        assert restored is not None, "Should be able to undo"
        assert restored['action_num'] == 2, "Should undo last action only"
        assert restored['remaining_ap'] == 5, "Should restore AP from last action"
        
        # Can't undo again
        second_undo = self.history.undo_last_action()
        assert second_undo is None, "Can't undo twice"
