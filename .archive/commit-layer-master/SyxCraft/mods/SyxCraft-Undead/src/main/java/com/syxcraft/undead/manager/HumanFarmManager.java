package com.syxcraft.undead.manager;

import com.syxcraft.undead.state.HumanFarmState;
import com.github.argon.sos.mod.sdk.api.GameApis;
import com.syxcraft.undead.constant.UndeadConstants;
import com.syxcraft.undead.util.ReflectionUtil;
import snake2d.util.file.FileGetter;
import snake2d.util.file.FilePutter;

import java.nio.file.Path;

/**
 * HumanFarmManager - manages the Human Farm (Human Village) on the world map.
 * Handles production, building gates, and farm state.
 */
public class HumanFarmManager {
    
    private final HumanFarmState state;
    private final com.github.argon.sos.mod.sdk.api.GameApis apis;
    
    public HumanFarmManager(com.syxcraft.undead.state.HumanFarmState state, 
                            com.github.argon.sos.mod.sdk.api.GameApis apis,
                            com.github.argon.sos.mod.sdk.properties.PropertiesStore props) {
        this.state = state;
        this.apis = apis;
    }
    
    public void update(double dt) {
        // 1. Check if Human Farm exists
        if (!state.hasHumanFarm()) return;
        
        // 2. Process production
        processProduction();
        
        // 3. Update farm level
        updateFarmLevel();
    }
    
    /**
     * Checks if Human Farm exists on world map.
     */
    public boolean hasHumanFarm() {
        return state.hasHumanFarm();
    }
    
    /**
     * Gets current farm level.
     */
    public int getFarmLevel() {
        return state.getFarmLevel();
    }
    
    /**
     * Gets current captive human count in farm.
     */
    public int getCaptiveHumanCount() {
        return state.getCaptiveHumanCount();
    }
    
    /**
     * Processes farm production of CAPTIVE_HUMAN.
     */
    private void processProduction() {
        int farmLevel = state.getFarmLevel();
        if (farmLevel <= 0) return;
        
        // Base production: 5 per day at level 1, scales with level^1.5
        double baseRate = 5.0;
        double levelMultiplier = Math.pow(state.getFarmLevel(), 1.5);
        double dailyProduction = baseRate * levelMultiplier;
        
        // Add to state (will be added to player stockpile in onGameUpdate)
        state.addPendingCaptiveHumans(dailyProduction / 365.0); // per tick (assuming 365 ticks per day)
    }
    
    /**
     * Updates farm level based on upgrades.
     */
    private void updateFarmLevel() {
        // Farm level is set via events when building is upgraded
    }
    
    /**
     * Adds captive humans from external source (Orc trade, raids, etc).
     */
    public void addCaptiveHumans(int amount) {
        state.addCaptiveHumans(amount);
    }
    
    /**
     * Consumes captive humans for conversion.
     * @return true if enough captive humans available
     */
    public boolean consumeCaptiveHumans(int amount) {
        return state.consumeCaptiveHumans(amount);
    }
    
    /**
     * Gets current captive human count available for conversion.
     */
    public int getAvailableCaptiveHumans() {
        return state.getCaptiveHumanCount();
    }
    
    /**
     * Checks if human farm exists on world map.
     */
    public boolean hasHumanFarm() {
        return state.hasHumanFarm();
    }
    
    /**
     * Sets human farm as established.
     */
    public void setHumanFarmEstablished(int regionId) {
        state.setHumanFarmEstablished(regionId);
    }
    
    /**
     * Gets the region ID where human farm is established.
     */
    public int getHumanFarmRegionId() {
        return state.getHumanFarmRegionId();
    }
    
    public void onGameSaved(snake2d.util.file.FilePutter putter) {
        state.onGameSaved(putter);
    }
    
    public void onGameLoaded(snake2d.util.file.FileGetter getter) {
        state.onGameLoaded(getter);
    }
}