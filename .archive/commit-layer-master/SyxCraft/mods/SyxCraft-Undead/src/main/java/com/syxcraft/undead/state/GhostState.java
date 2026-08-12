package com.syxcraft.undead.state;

import snake2d.util.file.FilePutter;
import snake2d.util.file.FileGetter;
import com.syxcraft.undead.constant.UndeadConstants;

/**
 * Geist State - tracks the control level of Undead over Human Village.
 * Replaces Vanilla Loyalty for Human race in Human Village.
 * 
 * Geist = 0.0 = full control, 1.0 = total rebellion
 * Updated every ON_GAME_UPDATE tick.
 * Persisted via FilePutter/FileGetter.
 */
public final class GhostState {
    
    // Current Geist value: 0.0 = full control, 1.0 = total rebellion
    private double geistValue = 0.0;
    
    // Components contributing to Geist
    private double controlLevel = 0.0;      // From control buildings (Wachturm, Garnison, Kerker)
    private double fearLevel = 0.0;         // From fear buildings (Galgen, Folterkammer, Hinrichtung)
    private double conditioningLevel = 0.0; // From conditioning buildings (Indoktrination, Propaganda, Ritual)
    
    // Event flags
    private boolean rebellionEventTriggered = false;
    private boolean criticalEventTriggered = false;
    
    // Constants
    private static final double REBELLION_THRESHOLD = 0.7;
    private static final double CRITICAL_THRESHOLD = 0.9;
    
    // Decay/Growth rates per day
    private static final double CONTROL_DECAY_PER_DAY = 0.02;
    private static final double FEAR_DECAY_PER_DAY = 0.01;
    private static final double CONDITIONING_GAIN_PER_DAY = 0.005;
    
    // Building contribution rates per day per building
    private static final double CONTROL_PER_BUILDING = 0.02;
    private static final double FEAR_PER_BUILDING = 0.03;
    private static final double CONDITIONING_PER_BUILDING = 0.005;
    
    // Max caps
    private static final double MAX_CONTROL = 0.5;
    private static final double MAX_FEAR = 0.6;
    private static final double MAX_CONDITIONING = 0.8;
    
    public GhostState() {}
    
    /**
     * Updates Geist value based on current building contributions and time delta.
     * Called every ON_GAME_UPDATE tick.
     * 
     * @param dt Time delta in days
     * @param controlBuildings Number of control buildings (Wachturm, Garnison, Kerker, etc.)
     * @param fearBuildings Number of fear buildings (Galgen, Folterkammer, etc.)
     * @param conditioningBuildings Number of conditioning buildings (Indoktrination, Propaganda, Ritual)
     */
    public void update(double dt, int controlBuildings, int fearBuildings, int conditioningBuildings) {
        // 1. Calculate building contributions
        double controlFromBuildings = Math.min(controlBuildings * CONTROL_PER_BUILDING, MAX_CONTROL);
        double fearFromBuildings = Math.min(fearBuildings * FEAR_PER_BUILDING, MAX_FEAR);
        double conditioningFromBuildings = Math.min(conditioningBuildings * CONDITIONING_PER_BUILDING, MAX_CONDITIONING);
        
        // 2. Update component levels with decay/growth
        controlLevel = Math.clamp(controlLevel + (controlFromBuildings - controlLevel) * 0.1 - CONTROL_DECAY_PER_DAY * 1.0, 0.0, MAX_CONTROL);
        fearLevel = Math.clamp(fearLevel + (fearFromBuildings - fearLevel) * 0.1 - FEAR_DECAY_PER_DAY * 1.0, 0.0, MAX_FEAR);
        conditioningLevel = Math.clamp(conditioningLevel + (conditioningFromBuildings - conditioningLevel) * 0.1 + CONDITIONING_GAIN_PER_DAY, 0.0, MAX_CONDITIONING);
        
        // 3. Compute Geist value
        // High control = low geist (good for Undead)
        // High fear = low geist (fear maintains control)
        // High conditioning = low geist (conditioning maintains control)
        double controlFactor = 1.0 - controlLevel;      // 0 = full control
        double fearFactor = fearLevel;                   // 1 = max fear
        double conditioningFactor = 1.0 - conditioningLevel; // 0 = fully conditioned
        
        // Weighted combination: Control 50%, Fear 30%, Conditioning 20%
        double newGeist = (controlFactor * 0.5) + (fearFactor * 0.3) + (conditioningFactor * 0.2);
        
        this.geistValue = Math.clamp(newGeist, 0.0, 1.0);
        
        // 3. Check thresholds for events
        checkThresholds();
    }
    
    /**
     * Checks Geist thresholds and triggers events if crossed.
     * Should be called after update().
     */
    private void checkThresholds() {
        // Rebellion threshold (0.7)
        if (geistValue >= 0.7 && !rebellionTriggered) {
            rebellionTriggered = true;
            // Event will be triggered via GhostManager
        } else if (geistValue < 0.7) {
            rebellionTriggered = false; // Reset if geist drops
        }
        
        // Critical threshold (0.9)
        if (geistValue >= 0.9 && !criticalTriggered) {
            criticalTriggered = true;
            // Critical event will be triggered
        } else if (geistValue < 0.9) {
            criticalTriggered = false;
        }
    }
    
    /**
     * Checks if rebellion event should fire.
     */
    public boolean shouldTriggerRebellion() {
        return geistValue >= 0.7 && !rebellionTriggered;
    }
    
    /**
     * Checks if critical event should fire.
     */
    public boolean shouldTriggerCritical() {
        return geistValue >= 0.9 && !criticalTriggered;
    }
    
    /**
     * Marks rebellion event as triggered.
     */
    public void markRebellionTriggered() {
        this.rebellionTriggered = true;
    }
    
    /**
     * Marks critical event as triggered.
     */
    public void markCriticalTriggered() {
        this.criticalTriggered = true;
    }
    
    /**
     * Adds control from Undead capital buildings.
     */
    public void addControlFromCapital(int buildingCount) {
        // Called when Undead capital builds control buildings
        // This directly adds to controlLevel
    }
    
    /**
     * Resets rebellion/critical flags (e.g., after event resolution).
     */
    public void resetEventFlags() {
        this.rebellionTriggered = false;
        this.criticalTriggered = false;
    }
    
    // Getters
    public double getGeistValue() { return geistValue; }
    public double getControlLevel() { return controlLevel; }
    public double getFearLevel() { return fearLevel; }
    public double getConditioningLevel() { return conditioningLevel; }
    public boolean isRebellionActive() { return rebellionTriggered; }
    public boolean isCriticalActive() { return criticalTriggered; }
    
    // Save/Load
    public void write(snake2d.util.file.FilePutter putter) {
        putter.mark(1) // version
            .chars("GEIST_VALUE").chars(String.valueOf(geistValue))
            .chars("CONTROL_LEVEL").chars(String.valueOf(controlLevel))
            .chars("FEAR_LEVEL").chars(String.valueOf(fearLevel))
            .chars("CONDITIONING_LEVEL").chars(String.valueOf(conditioningLevel))
            .chars("REBELLION_ACTIVE").chars(String.valueOf(rebellionTriggered))
            .chars("CRITICAL_ACTIVE").chars(String.valueOf(criticalTriggered));
    }
    
    public void read(snake2d.util.file.FileGetter getter) {
        getter.check(); // validates version
        this.geistValue = Double.parseDouble(getter.chars("GEIST_VALUE"));
        this.controlLevel = Double.parseDouble(getter.chars("CONTROL_LEVEL"));
        this.fearLevel = Double.parseDouble(getter.chars("FEAR_LEVEL"));
        this.conditioningLevel = Double.parseDouble(getter.chars("CONDITIONING_LEVEL"));
        this.rebellionTriggered = Boolean.parseBoolean(getter.chars("REBELLION_ACTIVE"));
        this.criticalTriggered = Boolean.parseBoolean(getter.chars("CRITICAL_ACTIVE"));
    }
    
    @Override
    public String toString() {
        return String.format("GhostState[geist=%.2f, control=%.2f, fear=%.2f, conditioning=%.2f, rebellion=%b, critical=%b]",
            geistValue, controlLevel, fearLevel, conditioningLevel, rebellionTriggered, criticalTriggered);
    }
}