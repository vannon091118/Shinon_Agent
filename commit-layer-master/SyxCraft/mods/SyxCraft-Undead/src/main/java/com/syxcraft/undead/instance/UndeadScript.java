package com.syxcraft.undead.instance;

import com.github.argon.sos.mod.sdk.api.GameApis;
import com.github.argon.sos.mod.sdk.phase.PhaseManager;
import com.github.argon.sos.mod.sdk.phase.Phases;
import com.github.argon.sos.mod.sdk.phase.state.StateManager;
import com.github.argon.sos.mod.sdk.api.GameApis;
import com.github.argon.sos.mod.sdk.properties.PropertiesStore;
import script.SCRIPT;
import script.SCRIPT_INSTANCE;

import snake2d.util.file.FilePutter;
import snake2d.util.file.FileGetter;
import java.nio.file.Path;

/**
 * UndeadScript - Main entry point for SyxCraft Undead Overhaul.
 * Implements SCRIPT interface for Mod SDK.
 */
public class UndeadScript implements SCRIPT {
    
    private static final com.syxcraft.undead.constant.UndeadConstants.Info INFO = 
        new com.syxcraft.undead.constant.UndeadConstants.Info("SyxCraft Undead Overhaul", "WoW-inspired Undead faction with dual-city management");
    
    @Override
    public CharSequence name() {
        return "SyxCraft Undead Overhaul";
    }
    
    @Override
    public CharSequence desc() {
        return "WoW-inspired Undead faction with dual-city management, geist system, and conversion mechanics.";
    }
    
    @Override
    public boolean initBeforeGameCreated() {
        return false;
    }
    
    @Override
    public boolean isSelectable() {
        return true;
    }
    
    @Override
    public boolean forceInit() {
        return false;
    }
    
    @Override
    public SCRIPT_INSTANCE createInstance() {
        return new UndeadInstance();
    }
}