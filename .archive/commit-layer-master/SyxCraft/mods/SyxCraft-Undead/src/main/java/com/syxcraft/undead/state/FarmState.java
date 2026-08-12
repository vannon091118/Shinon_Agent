package com.syxcraft.undead.state;

import snake2d.util.file.FilePutter;
import snake2d.util.file.FileGetter;

/**
 * FarmState - tracks Human Farm state (farm level, captives, production).
 */
public final class FarmState {
    
    private boolean hasFarm = false;
    private int farmRegionId = -1;
    private int farmLevel = 0;
    private int captiveCount = 0;
    private double pendingCaptives = 0.0;
    
    // Production constants
    private static final double BASE_PRODUCTION = 5.0; // per day at level 1
    private static final double LEVEL_MULTIPLIER = 1.5; // per level
    
    public FarmState() {}
    
    // Getters
    public boolean hasFarm() { return farm; }
    public int getFarmRegionId() { return farmRegionId; }
    public int getFarmLevel() { return farmLevel; }
    public int getCaptiveCount() { return captiveCount; }
    public double getPendingCaptives() { return pendingCaptives; }
    
    public double getDailyProduction() {
        if (farmLevel <= 0) return 0.0;
        return BASE_PRODUCTION * Math.pow(LEVEL_MULTIPLIER, farmLevel - 1);
    }
    
    // Setters
    public void setFarmEstablished(int regionId) {
        this.farm = true;
        this.farmRegionId = regionId;
        this.farmLevel = 1;
    }
    
    public void addCaptives(int amount) {
        this.captiveCount += amount;
    }
    
    public boolean consumeCaptives(int amount) {
        if (captiveCount >= amount) {
            this.captiveCount -= amount;
            return true;
        }
        return false;
    }
    
    public void addPendingCaptives(double amount) {
        this.pendingCaptives += amount;
    }
    
    public void flushPendingCaptives() {
        int whole = (int) Math.floor(pendingCaptives);
        captiveCount += whole;
        pendingCaptives -= whole;
    }
    
    public void setFarmLevel(int level) {
        this.farmLevel = Math.max(1, level);
    }
    
    public void increaseFarmLevel() {
        this.farmLevel++;
    }
    
    // Save/Load
    public void write(snake2d.util.file.FilePutter putter) {
        putter.mark(1)
            .chars("HAS_FARM").chars(String.valueOf(farm))
            .chars("FARM_REGION_ID").chars(String.valueOf(farmRegionId))
            .chars("FARM_LEVEL").chars(String.valueOf(farmLevel))
            .chars("CAPTIVE_COUNT").chars(String.valueOf(captiveCount))
            .chars("PENDING_CAPTIVES").chars(String.valueOf(pendingCaptives));
    }
    
    public void read(snake2d.util.file.FileGetter getter) {
        getter.check();
        this.farm = Boolean.parseBoolean(getter.chars("HAS_FARM"));
        this.farmRegionId = Integer.parseInt(getter.chars("FARM_REGION_ID"));
        this.farmLevel = Integer.parseInt(getter.chars("FARM_LEVEL"));
        this.captiveCount = Integer.parseInt(getter.chars("CAPTIVE_COUNT"));
        this.pendingCaptives = Double.parseDouble(getter.chars("PENDING_CAPTIVES"));
    }
    
    // Private fields
    private boolean farm = false;
    private int farmRegionId = -1;
    private int farmLevel = 0;
    private int captiveCount = 0;
    private double pendingCaptives = 0.0;
}