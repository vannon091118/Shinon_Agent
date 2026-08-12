package com.syxcraft.undead.state;

import snake2d.util.file.FilePutter;
import snake2d.util.file.FileGetter;

/**
 * HumanFarmState - tracks Human Farm state.
 * Manages farm level, captive human count, production.
 */
public final class HumanFarmState {
    
    private boolean hasHumanFarm = false;
    private int farmRegionId = -1;
    private int farmLevel = 0;
    private int captiveHumanCount = 0;
    private int pendingCaptiveHumans = 0; // Production pending add
    
    // Production
    private static final double BASE_PRODUCTION = 5.0; // per day at level 1
    private static final double LEVEL_MULTIPLIER = 1.5;
    
    public HumanFarmState() {}
    
    // Getters
    public boolean hasHumanFarm() { return hasHumanFarm; }
    public int getFarmLevel() { return farmLevel; }
    public int getFarmRegionId() { return farmRegionId; }
    public int getCaptiveHumanCount() { return captiveHumanCount; }
    public int getPendingCaptiveHumans() { return pendingCaptiveHumans; }
    
    // Setters
    public void setHumanFarmEstablished(int regionId) {
        this.hasHumanFarm = true;
        this.farmRegionId = farmRegionId;
        this.farmLevel = 1;
    }
    
    public void addCaptiveHumans(int amount) {
        this.captiveHumanCount += amount;
    }
    
    public boolean consumeCaptiveHumans(int amount) {
        if (captiveHumanCount >= amount) {
            this.captiveHumanCount -= amount;
            return true;
        }
        return false;
    }
    
    public void addPendingCaptiveHumans(double amount) {
        this.pendingCaptiveHumans += amount;
    }
    
    public void flushPendingCaptiveHumans() {
        this.captiveHumanCount += (int) Math.floor(pendingCaptiveHumans);
        this.pendingCaptiveHumans = this.pendingCaptiveHumans % 1.0;
    }
    
    public void setFarmLevel(int level) {
        this.farmLevel = Math.max(1, level);
    }
    
    public void increaseFarmLevel() {
        this.farmLevel++;
    }
    
    public double getDailyProduction() {
        return BASE_PRODUCTION * Math.pow(LEVEL_MULTIPLIER, farmLevel - 1);
    }
    
    // Save/Load
    public void write(FilePutter putter) {
        putter.mark(1)
            .chars("HAS_FARM").chars(String.valueOf(hasHumanFarm))
            .chars("FARM_REGION_ID").chars(String.valueOf(farmRegionId))
            .chars("FARM_LEVEL").chars(String.valueOf(farmLevel))
            .chars("CAPTIVE_HUMAN_COUNT").chars(String.valueOf(captiveHumanCount))
            .chars("PENDING_CAPTIVES").chars(String.valueOf(pendingCaptiveHumans));
    }
    
    public void read(FileGetter getter) {
        getter.check();
        this.hasHumanFarm = Boolean.parseBoolean(getter.chars("HAS_FARM"));
        this.farmRegionId = Integer.parseInt(getter.chars("FARM_REGION_ID"));
        this.farmLevel = Integer.parseInt(getter.chars("FARM_LEVEL"));
        this.captiveHumanCount = Integer.parseInt(getter.chars("CAPTIVE_HUMAN_COUNT"));
        this.pendingCaptiveHumans = Double.parseDouble(getter.chars("PENDING_CAPTIVES"));
    }
}