"""
Tests for CombatResolver (Phase 2.7).

Run with: python test_combat_resolver.py
"""

import sys
sys.path.insert(0, '.')

from core.combat_resolver import CombatResolver
from core.dice import DiceRoller


def test_deck_gun_range_1_2():
    """Test deck gun at range 1-2 (need 7+ on 2d6)."""
    print("\n=== Testing Deck Gun Range 1-2 ===")
    
    dice = DiceRoller(seed=42)
    resolver = CombatResolver(dice)
    
    # Test at range 1
    hit, roll, desc = resolver.resolve_deck_gun_attack(1)
    print(f"Range 1: roll={roll}, hit={hit}")
    print(f"  Description: {desc}")
    assert "Range 1-2" in desc, "Should indicate range 1-2"
    assert f"need 7+" in desc, "Should show target number"
    assert isinstance(hit, bool), "Should return boolean hit result"
    assert 2 <= roll <= 12, "2d6 roll should be between 2 and 12"
    
    # Test at range 2
    hit, roll, desc = resolver.resolve_deck_gun_attack(2)
    print(f"Range 2: roll={roll}, hit={hit}")
    assert "Range 1-2" in desc, "Should indicate range 1-2"
    
    print("✅ Deck gun range 1-2 tests passed!\n")


def test_deck_gun_range_3():
    """Test deck gun at range 3 (need 8+ on 2d6)."""
    print("\n=== Testing Deck Gun Range 3 ===")
    
    dice = DiceRoller(seed=100)
    resolver = CombatResolver(dice)
    
    # Test at range 3
    hit, roll, desc = resolver.resolve_deck_gun_attack(3)
    print(f"Range 3: roll={roll}, hit={hit}")
    print(f"  Description: {desc}")
    assert "Range 3" in desc, "Should indicate range 3"
    assert "need 8+" in desc, "Should show target number"
    assert 2 <= roll <= 12, "2d6 roll should be between 2 and 12"
    
    print("✅ Deck gun range 3 tests passed!\n")


def test_deck_gun_out_of_range():
    """Test deck gun out of range."""
    print("\n=== Testing Deck Gun Out of Range ===")
    
    dice = DiceRoller()
    resolver = CombatResolver(dice)
    
    # Range 0 (invalid)
    hit, _, desc = resolver.resolve_deck_gun_attack(0)
    print(f"Range 0: hit={hit}, desc='{desc}'")
    assert not hit, "Should not hit at range 0"
    assert "Invalid" in desc, "Should indicate invalid range"
    
    # Range 4 (too far)
    hit, _, desc = resolver.resolve_deck_gun_attack(4)
    print(f"Range 4: hit={hit}, desc='{desc}'")
    assert not hit, "Should not hit at range 4"
    assert "Out of range" in desc, "Should indicate out of range"
    assert "max 3" in desc, "Should mention max range"
    
    print("✅ Deck gun out of range tests passed!\n")


def test_deck_gun_damage():
    """Test deck gun damage roll."""
    print("\n=== Testing Deck Gun Damage ===")
    
    dice = DiceRoller(seed=42)
    resolver = CombatResolver(dice)
    
    # Roll damage
    damage, desc = resolver.roll_deck_gun_damage()
    print(f"Damage roll: {damage}")
    print(f"  Description: {desc}")
    assert 1 <= damage <= 6, "Damage should be 1d6 (1-6)"
    assert "Damage roll" in desc, "Should describe damage roll"
    assert "Allied Ship Damage Chart" in desc, "Should mention damage chart"
    
    print("✅ Deck gun damage tests passed!\n")


def test_torpedo_range_1_2_side():
    """Test torpedo at range 1-2 against side (need 3+ on 1d6)."""
    print("\n=== Testing Torpedo Range 1-2 Side ===")
    
    dice = DiceRoller(seed=42)
    resolver = CombatResolver(dice)
    
    # Fire 1 torpedo
    result = resolver.resolve_torpedo_attack(1, "side", 1)
    print(f"Range 1, Side, 1 torpedo:")
    print(f"  Target: {result['target']}+")
    print(f"  Rolls: {result['rolls']}")
    print(f"  Hits: {result['hits']}")
    print(f"  Description: {result['description']}")
    
    assert result['target'] == 3, "Should need 3+ at range 1-2 side"
    assert len(result['rolls']) == 1, "Should have 1 roll for 1 torpedo"
    assert all(1 <= r <= 6 for r in result['rolls']), "Rolls should be 1d6"
    assert "Range 1-2" in result['description'], "Should show range"
    assert "Side" in result['description'], "Should show aspect"
    
    # Fire 3 torpedoes
    result = resolver.resolve_torpedo_attack(2, "side", 3)
    print(f"\nRange 2, Side, 3 torpedoes:")
    print(f"  Rolls: {result['rolls']}")
    print(f"  Hits: {result['hits']}")
    
    assert len(result['rolls']) == 3, "Should have 3 rolls for 3 torpedoes"
    assert 0 <= result['hits'] <= 3, "Hits should be 0-3"
    
    print("✅ Torpedo range 1-2 side tests passed!\n")


def test_torpedo_range_aspects():
    """Test torpedo hit numbers for different aspects."""
    print("\n=== Testing Torpedo Range Aspects ===")
    
    dice = DiceRoller(seed=100)
    resolver = CombatResolver(dice)
    
    # Range 1-2: Side 3+, Front/Rear 4+
    result_side = resolver.resolve_torpedo_attack(1, "side", 1)
    result_fr = resolver.resolve_torpedo_attack(1, "front_rear", 1)
    print(f"Range 1-2: Side target={result_side['target']}, F/R target={result_fr['target']}")
    assert result_side['target'] == 3, "Range 1-2 side should need 3+"
    assert result_fr['target'] == 4, "Range 1-2 front/rear should need 4+"
    
    # Range 3-4: Side 4+, Front/Rear 5+
    result_side = resolver.resolve_torpedo_attack(3, "side", 1)
    result_fr = resolver.resolve_torpedo_attack(4, "front_rear", 1)
    print(f"Range 3-4: Side target={result_side['target']}, F/R target={result_fr['target']}")
    assert result_side['target'] == 4, "Range 3-4 side should need 4+"
    assert result_fr['target'] == 5, "Range 3-4 front/rear should need 5+"
    
    # Range 5-6: Side 5+, Front/Rear 6+
    result_side = resolver.resolve_torpedo_attack(5, "side", 1)
    result_fr = resolver.resolve_torpedo_attack(6, "front_rear", 1)
    print(f"Range 5-6: Side target={result_side['target']}, F/R target={result_fr['target']}")
    assert result_side['target'] == 5, "Range 5-6 side should need 5+"
    assert result_fr['target'] == 6, "Range 5-6 front/rear should need 6+"
    
    # Range 7-9: Side 6+, Front/Rear 6+
    result_side = resolver.resolve_torpedo_attack(7, "side", 1)
    result_fr = resolver.resolve_torpedo_attack(9, "front_rear", 1)
    print(f"Range 7-9: Side target={result_side['target']}, F/R target={result_fr['target']}")
    assert result_side['target'] == 6, "Range 7-9 side should need 6+"
    assert result_fr['target'] == 6, "Range 7-9 front/rear should need 6+"
    
    print("✅ Torpedo range aspects tests passed!\n")


def test_torpedo_invalid_inputs():
    """Test torpedo with invalid inputs."""
    print("\n=== Testing Torpedo Invalid Inputs ===")
    
    dice = DiceRoller()
    resolver = CombatResolver(dice)
    
    # Invalid range (0)
    result = resolver.resolve_torpedo_attack(0, "side", 1)
    print(f"Range 0: hits={result['hits']}, desc='{result['description']}'")
    assert result['hits'] == 0, "Should have 0 hits for invalid range"
    assert "Invalid range" in result['description'], "Should indicate invalid range"
    
    # Invalid range (10)
    result = resolver.resolve_torpedo_attack(10, "side", 1)
    print(f"Range 10: hits={result['hits']}, desc='{result['description']}'")
    assert result['hits'] == 0, "Should have 0 hits for out of range"
    assert "Invalid range" in result['description'], "Should indicate invalid range"
    
    # Invalid aspect
    result = resolver.resolve_torpedo_attack(1, "top", 1)
    print(f"Invalid aspect: hits={result['hits']}, desc='{result['description']}'")
    assert result['hits'] == 0, "Should have 0 hits for invalid aspect"
    assert "Invalid aspect" in result['description'], "Should indicate invalid aspect"
    
    # Invalid torpedo count (0)
    result = resolver.resolve_torpedo_attack(1, "side", 0)
    print(f"0 torpedoes: hits={result['hits']}, desc='{result['description']}'")
    assert result['hits'] == 0, "Should have 0 hits for 0 torpedoes"
    assert "Invalid torpedo count" in result['description'], "Should indicate invalid count"
    
    # Invalid torpedo count (4)
    result = resolver.resolve_torpedo_attack(1, "side", 4)
    print(f"4 torpedoes: hits={result['hits']}, desc='{result['description']}'")
    assert result['hits'] == 0, "Should have 0 hits for 4 torpedoes"
    assert "Invalid torpedo count" in result['description'], "Should indicate invalid count"
    
    print("✅ Torpedo invalid inputs tests passed!\n")


def test_torpedo_damage():
    """Test torpedo damage rolls."""
    print("\n=== Testing Torpedo Damage ===")
    
    dice = DiceRoller(seed=42)
    resolver = CombatResolver(dice)
    
    # 0 hits
    damages = resolver.roll_torpedo_damage(0)
    print(f"0 hits: {len(damages)} damage rolls")
    assert len(damages) == 0, "Should have 0 damage rolls for 0 hits"
    
    # 1 hit
    damages = resolver.roll_torpedo_damage(1)
    print(f"1 hit: damage={damages[0][0]}, desc='{damages[0][1]}'")
    assert len(damages) == 1, "Should have 1 damage roll for 1 hit"
    assert 1 <= damages[0][0] <= 6, "Damage should be 1d6"
    assert "Hit 1 damage" in damages[0][1], "Should describe hit 1"
    
    # 3 hits
    damages = resolver.roll_torpedo_damage(3)
    print(f"3 hits:")
    for i, (dmg, desc) in enumerate(damages, 1):
        print(f"  Hit {i}: damage={dmg}, desc='{desc}'")
        assert 1 <= dmg <= 6, f"Hit {i} damage should be 1d6"
        assert f"Hit {i} damage" in desc, f"Should describe hit {i}"
    assert len(damages) == 3, "Should have 3 damage rolls for 3 hits"
    
    print("✅ Torpedo damage tests passed!\n")


def test_combat_summary():
    """Test combat summary info."""
    print("\n=== Testing Combat Summary ===")
    
    dice = DiceRoller()
    resolver = CombatResolver(dice)
    
    # Deck gun summaries
    summary = resolver.get_combat_summary("deck_gun", 1)
    print(f"Deck gun range 1: {summary}")
    assert "7+" in summary and "2d6" in summary, "Should show deck gun info"
    
    summary = resolver.get_combat_summary("deck_gun", 3)
    print(f"Deck gun range 3: {summary}")
    assert "8+" in summary and "2d6" in summary, "Should show harder target at range 3"
    
    summary = resolver.get_combat_summary("deck_gun", 5)
    print(f"Deck gun range 5: {summary}")
    assert "out of range" in summary.lower(), "Should indicate out of range"
    
    # Torpedo summaries
    summary = resolver.get_combat_summary("torpedo", 1, "side")
    print(f"Torpedo range 1 side: {summary}")
    assert "3+" in summary and "1d6" in summary and "Side" in summary, "Should show torpedo info"
    
    summary = resolver.get_combat_summary("torpedo", 8, "front_rear")
    print(f"Torpedo range 8 front/rear: {summary}")
    assert "6+" in summary and "Front/Rear" in summary, "Should show long range info"
    
    print("✅ Combat summary tests passed!\n")


def test_hit_chances_info():
    """Test hit probability info displays."""
    print("\n=== Testing Hit Chances Info ===")
    
    dice = DiceRoller()
    resolver = CombatResolver(dice)
    
    # Deck gun hit chances
    deck_gun_info = resolver.get_deck_gun_hit_chances()
    print("Deck Gun Hit Chances:")
    print(deck_gun_info)
    assert "7+" in deck_gun_info and "2d6" in deck_gun_info, "Should show deck gun chances"
    assert "58.3%" in deck_gun_info, "Should show probability for 7+"
    assert "41.7%" in deck_gun_info, "Should show probability for 8+"
    
    # Torpedo hit chances
    torpedo_info = resolver.get_torpedo_hit_chances()
    print("\nTorpedo Hit Chances:")
    print(torpedo_info)
    assert "1d6" in torpedo_info, "Should show 1d6 rolls"
    assert "Side" in torpedo_info and "Front/Rear" in torpedo_info, "Should show both aspects"
    assert "Range 1-2" in torpedo_info, "Should show range bands"
    assert "%" in torpedo_info, "Should show percentages"
    
    print("✅ Hit chances info tests passed!\n")


def test_deterministic_rolls():
    """Test that seeded dice produce consistent results."""
    print("\n=== Testing Deterministic Rolls ===")
    
    # First resolver with seed
    dice1 = DiceRoller(seed=12345)
    resolver1 = CombatResolver(dice1)
    
    # Second resolver with same seed
    dice2 = DiceRoller(seed=12345)
    resolver2 = CombatResolver(dice2)
    
    # Deck gun attacks should match
    hit1, roll1, _ = resolver1.resolve_deck_gun_attack(2)
    hit2, roll2, _ = resolver2.resolve_deck_gun_attack(2)
    print(f"Seeded deck gun: roll1={roll1}, roll2={roll2}")
    assert roll1 == roll2, "Same seed should produce same roll"
    assert hit1 == hit2, "Same seed should produce same result"
    
    # Torpedo attacks should match
    result1 = resolver1.resolve_torpedo_attack(1, "side", 3)
    result2 = resolver2.resolve_torpedo_attack(1, "side", 3)
    print(f"Seeded torpedoes: rolls1={result1['rolls']}, rolls2={result2['rolls']}")
    assert result1['rolls'] == result2['rolls'], "Same seed should produce same rolls"
    assert result1['hits'] == result2['hits'], "Same seed should produce same hits"
    
    print("✅ Deterministic rolls tests passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2.7 Tests - CombatResolver")
    print("=" * 60)
    
    try:
        test_deck_gun_range_1_2()
        test_deck_gun_range_3()
        test_deck_gun_out_of_range()
        test_deck_gun_damage()
        test_torpedo_range_1_2_side()
        test_torpedo_range_aspects()
        test_torpedo_invalid_inputs()
        test_torpedo_damage()
        test_combat_summary()
        test_hit_chances_info()
        test_deterministic_rolls()
        
        print("=" * 60)
        print("✅ ALL COMBAT RESOLVER TESTS PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
