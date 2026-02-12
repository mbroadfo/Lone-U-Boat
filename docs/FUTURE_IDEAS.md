# Future Ideas & Feature Wishlist

**Last Updated:** February 10, 2026

This document consolidates future feature ideas and enhancement proposals for Lone U-Boat. Items here are not scheduled for implementation but represent potential improvements.

---

## Phase 5 Priorities (Immediate Opportunities)

### Save/Load System
- Save game state mid-mission
- Resume from saved games
- Auto-save on phase transitions
- Save file management UI
- Quick save/load hotkeys

### Sound Effects & Audio
- Torpedo fire/hit sounds
- Depth charge explosions
- Sonar pings for detection
- Ship destruction audio
- Phase transition sounds
- Background ambient water sounds
- Victory/defeat music stings

### Tutorial/Help System
- In-game help overlay (F1 key)
- Action tooltips on hover
- Quick reference card (keyboard shortcuts)
- First-time player guided walkthrough
- Interactive tutorial mission
- Context-sensitive help

### UI Polish & Quality of Life
- Animation system for movements/attacks
- Smooth camera transitions
- Hex highlighting improvements
- Better visual feedback for invalid actions
- Status effect icons and indicators
- Mini-map for large missions
- Zoom controls for board

---

## Mission Expansion

### Additional Missions
- Mission 2: Convoy Attack (multiple merchants + escorts)
- Mission 3: Harbor Infiltration (minefields, patrols)
- Mission 4: Long Range Patrol (fuel management)
- Mission 5: Wolf Pack Tactics (multiple U-boats)
- Mission 6: Atlantic Crossing (weather, aircraft)

### Mission Features
- Dynamic weather systems (affects detection, movement)
- Day/night cycle (visibility changes)
- Fuel management (limited AP based on fuel)
- Ammunition tracking (torpedo reloads)
- Mission objectives beyond "sink all ships"
  - Reconnaissance missions
  - Escort specific ship
  - Survive N turns
  - Reach destination hex

### Mission Editor
- Visual mission designer
- Drag-and-drop ship placement
- Event table editor
- Terrain editor (land, shallow water)
- Test/preview missions before playing

---

## Campaign Mode

### Career System
- Multi-mission campaign with persistent U-boat
- Crew experience and leveling
- U-boat upgrades between missions
- Historical progression (1939-1945)
- Port visits for repairs/refits
- Promotion system and decorations

### Strategic Layer
- World map with mission selection
- Intel gathering and mission planning
- Supply management
- Historical events affecting availability
- Enemy response to player success

---

## Multiplayer/AI Improvements

### Co-op Play
- 2-player wolf pack operations
- Coordinated attacks
- Shared detection levels
- Split-screen or network play

### Improved AI
- Multiple difficulty levels
- Adaptive escort behavior
- Convoy tactics (evasion, formation changes)
- Aircraft patrol patterns
- Enemy learns from player tactics

---

## Advanced Gameplay Systems

### Radio & Communication
- Radio intercepts (hints about convoys)
- Request air reconnaissance
- Call for wolf pack support
- Risk of radio direction finding

### Weather & Environment
- Storms (reduced detection, difficult movement)
- Fog (reduced visibility)
- Ice (Arctic missions)
- Current/tide effects on movement

### Enhanced Damage System
- Individual system damage (not just binary)
- Flooding mechanics (progressive damage)
- Fire damage
- Repair priorities and time requirements
- Jury-rigged repairs (temporary fixes)

### Crew Management
- Individual crew members with stats
- Fatigue system (long missions)
- Morale effects
- Crew injuries and medical system
- Training and specialization

---

## Presentation & Polish

### Graphics Enhancements
- High-resolution hex textures
- Ship sprites with multiple angles
- Water effects and animations
- Explosion effects
- Weather visual effects
- Particle systems

### UI Improvements
- Customizable UI layout
- Resizable panels
- Theme/color scheme options
- Accessibility options
  - Colorblind modes
  - Font size scaling
  - Screen reader support
- Hotkey customization

### Statistics & Replay
- Detailed mission statistics
- Lifetime career stats
- Replay system (watch previous missions)
- Screenshot/video capture
- Achievement system

---

## Technical Improvements

### Performance
- Optimize rendering for large maps
- Reduce memory usage
- Faster AI calculations
- Background loading of missions

### Modding Support
- Mission file format documentation
- Custom ship types
- Custom rules/tables
- Python scripting for events
- Steam Workshop integration

### Platform Support
- Mobile version (iOS/Android)
- Web browser version (WASM)
- Steam Deck optimization
- Controller support

---

## Documentation

### Player Resources
- Video tutorials
- Strategy guides
- Historical context notes
- FAQ and troubleshooting

### Developer Documentation
- Code architecture guide
- AI behavior documentation
- JSON schema reference
- Contribution guidelines

---

## Community Features

### Online Features
- Global leaderboards
- Mission sharing
- Replay sharing
- Community challenges

### Social
- Discord integration
- In-game chat
- Player profiles
- Friend system

---

## Out of Scope (For Now)

These are interesting but probably too ambitious:

- 3D graphics (keeping 2D hex-based)
- Real-time gameplay (turn-based is core)
- Non-submarine gameplay (focus on U-boat)
- Historical accuracy simulator (fun > realism)
- Battle of Atlantic grand strategy (too broad)

---

## Priority Matrix

**High Value, Low Effort:**
- Sound effects
- Save/load system
- Tutorial system
- Additional missions (using existing engine)

**High Value, High Effort:**
- Campaign mode
- Mission editor
- Advanced damage system
- Multiplayer

**Low Value, Low Effort:**
- UI themes
- Statistics tracking
- Achievement system

**Low Value, High Effort:**
- 3D graphics
- Mobile port
- Real-time mode

---

## Implementation Notes

When implementing features from this list:
1. Create dedicated branch for feature
2. Write tests first (TDD approach)
3. Update this document to move item to "In Progress"
4. Document completion in CHANGELOG.md
5. Remove from this document when complete

**Remember:** Focus on making existing features excellent before adding new ones. Quality over quantity!
