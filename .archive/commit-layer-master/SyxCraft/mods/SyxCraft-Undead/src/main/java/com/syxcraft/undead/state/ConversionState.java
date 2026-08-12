package com.syxcraft.undead.state;

import snake2d.util.file.FilePutter;
import snake2d.util.file.FileGetter;

/**
 * ConversionState - tracks conversion cooldowns and stats.
 */
public final class ConversionState {
    
    private double conversionCooldown = 0.0; // in years
    private int totalConversions = 0;
    private int totalCaptivesConverted = 0;
    private int totalEssenceSpent = 0;
    
    public ConversionState() {}
    
    // Getters
    public double getConversionCooldown() { return conversionCooldown; }
    public int getTotalConversions() { return totalConversions; }
    public int getTotalCaptivesConverted() { return totalCaptivesConverted; }
    public int getTotalEssenceSpent() { return totalEssenceSpent; }
    
    // Cooldown management
    public boolean isOnCooldown() {
        return conversionCooldown > 0;
    }
    
    public double getCooldownRemainingDays() {
        return conversionCooldown * 365.0;
    }
    
    public void setCooldown(double days) {
        this.conversionCooldown = days / 365.0;
    }
    
    public void reduceCooldown(double years) {
        this.conversionCooldown = Math.max(0, this.conversionCooldown - years);
    }
    
    public boolean isOnCooldown() {
        return conversionCooldown > 0;
    }
    
    public void recordConversion(int captives, int essence) {
        this.totalConversions++;
        this.totalCaptivesConverted += captives;
        this.totalEssenceSpent += captives; // 1 essence per conversion
    }
    
    // Save/Load
    public void write(snake2d.util.file.FilePutter putter) {
        putter.mark(1)
            .chars("COOLDOWN").chars(String.valueOf(conversionCooldown))
            .chars("TOTAL_CONVERSIONS").chars(String.valueOf(totalConversions))
            .chars("TOTAL_CAPTIVES_CONVERTED").chars(String.valueOf(totalCaptivesConverted))
            .chars("TOTAL_ESSENCE_SPENT").chars(String.valueOf(totalEssenceSpent));
    }
    
    public void read(snake2d.util.file.FileGetter getter) {
        getter.check();
        this.conversionCooldown = Double.parseDouble(getter.chars("COOLDOWN"));
        this.totalConversions = Integer.parseInt(getter.chars("TOTAL_CONVERSIONS"));
        this.totalCaptivesConverted = Integer.parseInt(getter.chars("TOTAL_CAPTIVES_CONVERTED"));
        this.totalEssenceSpent = Integer.parseInt(getter.chars("TOTAL_ESSENCE_SPENT"));
    }
}