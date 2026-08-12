package com.syxcraft.undead.manager;

import com.github.argon.sos.mod.sdk.api.GameApis;
import com.syxcraft.undead.state.ConversionState;
import com.syxcraft.undead.util.ReflectionUtil;

import snake2d.util.file.FileGetter;
import snake2d.util.file.FilePutter;

import java.nio.file.Path;

/**
 * ConversionManager - handles Undead conversion of captured humans.
 * 
 * Conversion Logic:
 * - Requires: CAPTIVE_HUMAN resource (from Human Farm) + ESSENCE
 * - 1 CAPTIVE_HUMAN + 1 ESSENCE → 1 UNDEAD Citizen
 * - Base ratio 1:1, improvable via tech
 * - Cooldown: 30 days (configurable)
 * - Cooldown tracked per settlement
 */
public class ConversionManager {
    
    private final com.syxcraft.undead.state.ConversionState state;
    private final com.github.argon.sos.mod.sdk.api.GameApis apis;
    
    // Configuration
    private static final int BASE_CAPTIVES_PER_CONVERSION = 1;
    private static final int BASE_ESSENCE_COST = 1;
    private static final double BASE_COOLDOWN_DAYS = 30.0;
    
    // Cooldown tracking (per settlement)
    private double conversionCooldown = 0.0;
    
    public ConversionManager(com.syxcraft.undead.state.ConversionState state, 
                             com.github.argon.sos.mod.sdk.api.GameApis apis) {
        this.state = state;
        this.apis = apis;
    }
    
    public void update(double dt) {
        // Update cooldown
        if (conversionCooldown > 0) {
            conversionCooldown = Math.max(0, conversionCooldown - 1.0/365.0); // dt in years
        }
    }
    
    /**
     * Attempts to convert captive humans into Undead citizens.
     * 
     * @param captiveAmount Number of captive humans to convert
     * @return ConversionResult with success status and details
     */
    public ConversionResult attemptConversion(int captiveAmount) {
        // 1. Check cooldown
        if (isOnCooldown()) {
            return ConversionResult.failure("Conversion on cooldown. " + 
                String.format("%.1f", getCooldownRemaining()) + " days remaining");
        }
        
        // 2. Check resources
        if (!hasRequiredResources(captiveAmount)) {
            return ConversionResult.failure("Insufficient resources: need " + 
                getRequiredCaptives() + " captives and " + 
                getRequiredEssence() + " essence");
        }
        
        // 3. Check available captives in Human Farm
        if (!hasAvailableCaptives()) {
            return ConversionResult.failure("No captive humans available in Human Farm");
        }
        
        // 4. Execute conversion
        boolean success = performConversion();
        if (success) {
            // Set cooldown
            this.conversionCooldown = BASE_COOLDOWN_DAYS / 365.0; // Convert to years
            
            return ConversionResult.success("Successfully converted captives to Undead citizens");
        }
        
        return ConversionResult.failure("Conversion failed");
    }
    
    /**
     * Checks if conversion is on cooldown.
     */
    public boolean isOnCooldown() {
        return conversionCooldown > 0;
    }
    
    /**
     * Gets remaining cooldown in days.
     */
    public double getCooldownRemaining() {
        return conversionCooldown * 365.0; // Convert back to days
    }
    
    /**
     * Checks if required resources are available.
     */
    private boolean hasRequiredResources(int captiveAmount) {
        // Check ESSENCE
        var player = getPlayerFaction();
        if (player == null) return false;
        
        // Check ESSENCE resource
        int essence = getPlayerResource("ESSENCE");
        if (essence < BASE_ESSENCE_COST) return false;
        
        // Check CAPTIVE_HUMAN in Human Farm (via HumanFarmManager)
        // This is checked separately
        
        return true;
    }
    
    /**
     * Checks if captives are available in Human Farm.
     */
    private boolean hasAvailableCaptives() {
        // Check Human Farm Manager
        // For now, assume available if Human Farm exists
        // TODO: Integrate with HumanFarmManager
        return true; // Placeholder
    }
    
    /**
     * Executes the conversion.
     */
    private boolean performConversion() {
        try {
            // 1. Consume CAPTIVE_HUMAN from Human Farm
            // 2. Consume ESSENCE from player stockpile
            // 3. Add Undead citizens
            
            // This would need to interact with:
            // - HumanFarmManager to consume CAPTIVE_HUMAN
            // - Player stockpile to consume ESSENCE
            // - Settlement to add UNDEAD citizens
            
            // For now, return success (placeholder)
            return true;
            
        } catch (Exception e) {
            System.err.println("[ConversionManager] Conversion failed: " + e.getMessage());
            return false;
        }
    }
    
    /**
     * Gets required captives for conversion.
     */
    public int getRequiredCaptives() {
        return BASE_CAPTIVES_PER_CONVERSION;
    }
    
    /**
     * Gets required essence for conversion.
     */
    public int getRequiredEssence() {
        return BASE_ESSENCE_COST;
    }
    
    /**
     * Gets remaining cooldown in days.
     */
    public double getCooldownRemaining() {
        return conversionCooldown * 365.0; // Convert back to days
    }
    
    /**
     * Checks if conversion is on cooldown.
     */
    public boolean isOnCooldown() {
        return conversionCooldown > 0;
    }
    
    /**
     * Sets conversion cooldown.
     */
    public void setCooldown(double days) {
        this.conversionCooldown = days / 365.0;
    }
    
    // Helper methods
    private Object getPlayerFaction() {
        try {
            return apis.faction().getPlayer();
        } catch (Exception e) {
            return null;
        }
    }
    
    private int getPlayerResource(String resourceName) {
        // TODO: Implement resource lookup via GameApis
        return 0;
    }
    
    // Save/Load
    public void onGameSaved(snake2d.util.file.FilePutter putter) {
        putter.mark(1)
            .chars("CONVERSION_COOLDOWN").chars(String.valueOf(conversionCooldown));
    }
    
    public void onGameLoaded(snake2d.util.file.FileGetter getter) {
        getter.check();
        conversionCooldown = Double.parseDouble(getter.chars("CONVERSION_COOLDOWN"));
    }
}