package com.syxcraft.undead;

import script.SCRIPT;
import script.SCRIPT_INSTANCE;
import util.info.INFO;
import com.github.argon.sos.mod.sdk.api.GameApis;
import com.github.argon.sos.mod.sdk.phase.PhaseManager;
import com.github.argon.sos.mod.sdk.phase.state.StateManager;
import com.github.argon.sos.mod.sdk.properties.PropertiesStore;
import com.syxcraft.undead.manager.*;
import com.syxcraft.undead.state.*;

/**
 * UndeadScript - Entry point for SyxCraft Undead Overhaul.
 * Implements SCRIPT interface for Songs of Syx modding.
 */
public final class UndeadScript implements SCRIPT {
    
    private static final INFO INFO = new INFO(
        "SyxCraft Undead Overhaul", 
        "WoW-inspired Undead faction with dual-city management and human conversion mechanics."
    );
    
    @Override
    public CharSequence name() {
        return INFO.name;
    }
    
    @Override
    public CharSequence desc() {
        return INFO.desc;
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