package com.syxcraft.undead.instance;

import script.SCRIPT;
import script.SCRIPT_INSTANCE;
import com.github.argon.sos.mod.sdk.api.GameApis;
import com.github.argon.sos.mod.sdk.phase.PhaseManager;
import com.github.argon.sos.mod.sdk.phase.state.StateManager;
import com.github.argon.sos.mod.sdk.properties.PropertiesStore;
import com.syxcraft.undead.manager.*;
import com.syxcraft.undead.state.*;
import snake2d.util.file.FilePutter;
import snake2d.util.file.FileGetter;
import java.nio.file.Path;

/**
 * UndeadInstance - Main script instance for SyxCraft Undead.
 * Implements SCRIPT_INSTANCE interface for game lifecycle hooks.
 */
public final class UndeadInstance implements SCRIPT_INSTANCE {
    
    // Managers
    private final HumanFarmManager humanFarmManager;
    private final ConversionManager conversionManager;
    private final GhostManager ghostManager;
    private final GateManager gateManager;
    private final DualSettlementManager dualSettlementManager;
    private final OrcTradeManager orcTradeManager;
    
    // State
    private final GhostState ghostState;
    private final HumanFarmState farmState;
    private final ConversionState conversionState;
    private final DualSettlementState dualSettlementState;
    private final ConversionState orcTradeState;
    
    // Dependencies
    private final com.github.argon.sos.mod.sdk.api.GameApis gameApis;
    private final PhaseManager phaseManager;
    private final StateManager stateManager;
    private final PropertiesStore propertiesStore;
    
    public UndeadInstance(
        PhaseManager phaseManager,
        StateManager stateManager,
        GameApis gameApis,
        PropertiesStore propertiesStore
    ) {
        this.phaseManager = phaseManager;
        this.stateManager = stateManager;
        this.gameApis = gameApis;
        this.propertiesStore = propertiesStore;
        
        // Initialize state objects
        this.ghostState = new GhostState();
        this.farmState = new HumanFarmState();
        this.conversionState = new ConversionState();
        this.dualSettlementState = new DualSettlementState();
        this.orcTradeState = new ConversionState(); // Reuse for Orc trade state
        
        // Initialize managers
        this.humanFarmManager = new HumanFarmManager(new HumanFarmState(), gameApis, propertiesStore);
        this.conversionManager = new ConversionManager(new ConversionState(), gameApis);
        this.ghostManager = new GhostManager(new GhostState(), gameApis);
        this.gateManager = new GateManager(gameApis);
        this.dualSettlementManager = new DualSettlementManager(new DualSettlementState(), gameApis);
        this.orcTradeManager = new OrcTradeManager(gameApis);
        
        // Register SDK Phases
        registerPhases();
    }
    
    private void registerPhases() {
        phaseManager.register(com.github.argon.sos.mod.sdk.phase.Phase.INIT_BEFORE_GAME_CREATED, 
            com.github.argon.sos.mod.sdk.phase.Phases.INIT_BEFORE_GAME_CREATED);
        phaseManager.register(com.github.argon.sos.mod.sdk.phase.Phase.INIT_GAME_RESOURCES_LOADED, 
            com.github.argon.sos.mod.sdk.phase.Phases.INIT_GAME_RESOURCES_LOADED);
        phaseManager.register(com.github.argon.sos.mod.sdk.phase.Phase.INIT_MOD_CREATE_INSTANCE, 
            com.github.argon.sos.mod.sdk.phase.Phases.INIT_MOD_CREATE_INSTANCE);
        phaseManager.register(com.github.argon.sos.mod.sdk.phase.Phase.ON_GAME_UPDATE, 
            com.github.argon.sos.mod.sdk.phase.Phases.ON_GAME_UPDATE);
        phaseManager.register(com.github.argon.sos.mod.sdk.phase.Phase.ON_GAME_SAVED, 
            com.github.argon.sos.mod.sdk.phase.Phases.ON_GAME_SAVED);
        phaseManager.register(com.github.argon.sos.mod.sdk.phase.Phase.ON_GAME_LOADED, 
            com.github.argon.sos.mod.sdk.phase.Phases.ON_GAME_LOADED);
        phaseManager.register(com.github.argon.sos.mod.sdk.phase.Phase.ON_GAME_SAVE_RELOADED, 
            com.github.argon.sos.mod.sdk.phase.Phases.ON_GAME_SAVE_RELOADED);
        phaseManager.register(com.github.argon.sos.mod.sdk.phase.Phase.INIT_NEW_GAME_SESSION, 
            com.github.argon.sos.mod.sdk.phase.Phases.INIT_NEW_GAME_SESSION);
        phaseManager.register(com.github.argon.sos.mod.sdk.phase.Phase.ON_GAME_SAVED, 
            com.github.argon.sos.mod.sdk.phase.Phases.ON_GAME_SAVED);
        phaseManager.register(com.github.argon.sos.mod.sdk.phase.Phase.ON_BEFORE_BATTLE, 
            com.github.argon.sos.mod.sdk.phase.Phases.ON_BEFORE_BATTLE);
        phaseManager.register(com.github.argon.sos.mod.sdk.phase.Phase.ON_BATTLE, 
            com.github.argon.sos.mod.sdk.phase.Phases.ON_BATTLE);
        phaseManager.register(com.github.argon.sos.mod.sdk.phase.Phase.ON_AFTER_BATTLE, 
            com.github.argon.sos.mod.sdk.phase.Phases.ON_AFTER_BATTLE);
        phaseManager.register(com.github.argon.sos.mod.sdk.phase.Phase.ON_CRASH, 
            com.github.argon.sos.mod.sdk.phase.Phases.ON_CRASH);
    }
    
    // ========== SCRIPT_INSTANCE Interface ==========
    
    @Override
    public void initBeforeGameCreated() {
        // Initialize dual settlement on new game
        dualSettlementManager.initDualSettlement();
        
        // Initialize Ghost System
        ghostManager.init();
    }
    
    @Override
    public void initBeforeGameInited() {
        // After game resources loaded, before game fully initialized
        dualSettlementManager.onGameResourcesLoaded();
    }
    
    @Override
    public void initModCreateInstance() {
        // Mod instance created
    }
    
    @Override
    public void initNewGameSession() {
        // New game session started
        dualSettlementManager.initDualSettlement();
        ghostManager.initGhostSystem();
        gateManager.init();
        humanFarmManager.init();
        conversionManager.init();
    }
    
    @Override
    public void onGameUpdate(double dt) {
        // Main update loop - order matters!
        // 1. Ghost System (Geist updates)
        ghostManager.update();
        
        // 2. Gate System (Building Gates)
        gateManager.update();
        
        // 3. Dual Settlement Manager
        dualSettlementManager.update();
        
        // 4. Human Farm Manager
        humanFarmManager.update();
        
        // 5. Conversion Manager
        conversionManager.update();
        
        // 6. Orc Trade Manager
        // orcTradeManager.update();
    }
    
    @Override
    public void onGameSaved(Path path, FilePutter putter) {
        // Save all state
        ghostManager.onGameSaved(path, putter);
        gateManager.onGameSaved(path, putter);
        dualSettlementManager.onGameSaved(path, putter);
        // ... other managers
    }
    
    @Override
    public void onGameLoaded(Path path, FileGetter getter) {
        // Load all state
        ghostManager.onGameLoaded(path, getter);
        gateManager.onGameLoaded(path);
        dualSettlementManager.onGameLoaded(path);
        // ... other managers
    }
    
    @Override
    public void onGameSaveReloaded() {
        // After save reload
    }
    
    @Override
    public void onBeforeBattle() {
        // Pre-battle
    }
    
    @Override
    public void onBattle() {
        // During battle
    }
    
    @Override
    public void onAfterBattle() {
        // Post-battle
    }
    
    @Override
    public void onCrash(Throwable throwable) {
        // Crash handling
        System.err.println("[SyxCraft Undead] Crash: " + throwable.getMessage());
        throwable.printStackTrace();
    }
    
    @Override
    public boolean handleBrokenSavedState() {
        // Allow broken saves to continue
        return true;
    }
    
    // Getters for managers
    public HumanFarmManager humanFarmManager() { return humanFarmManager; }
    public ConversionManager conversionManager() { return conversionManager; }
    public GhostManager ghostManager() { return ghostManager; }
    public GateManager gateManager() { return gateManager; }
    public DualSettlementManager dualSettlementManager() { return dualSettlementManager; }
    public OrcTradeManager orcTradeManager() { return orcTradeManager; }
}