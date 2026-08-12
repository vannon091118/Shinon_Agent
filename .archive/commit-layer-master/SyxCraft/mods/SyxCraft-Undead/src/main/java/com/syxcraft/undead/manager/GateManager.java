package com.syxcraft.undead.manager;

import com.github.argon.sos.mod.sdk.api.GameApis;
import com.syxcraft.undead.constant.UndeadConstants;

/**
 * GateManager - manages Building Gates (Building in Human Village unlocks function in Undead Capital).
 * 
 * Gates for MVP:
 * 1. BARRACKS (Military Building in Human Village) → Undead Military Buildings
 * 2. GRANARY (Food Storage) → Conversion Event
 * 3. WATCHTOWER → Geist Decay reduced
 */
public class GateManager {
    
    private final com.github.argon.sos.mod.sdk.api.GameApis apis;
    private final java.util.Set<String> unlockedGates = new java.util.HashSet<>();
    
    // Gate definitions
    private static final java.util.List<Gate> GATES = java.util.List.of(
        new Gate("BARRACKS", "UNDEAD_MILITARY_BUILDINGS", "Militärgebäude in der Undead-Hauptstadt"),
        new Gate("GRANARY", "UNDEAD_CONVERSION_EVENT", "Conversion-Event verfügbar"),
        new Gate("WATCHTOWER", "GEIST_DECAY_REDUCTION", "Geist-Decay um 20% reduziert")
    );
    
    public GateManager(com.github.argon.sos.mod.sdk.api.GameApis apis) {
        this.apis = apis;
    }
    
    /**
     * Updates gate status - scans Human Village for gate buildings.
     * Call from UndeadInstance.onGameUpdate()
     */
    public void update() {
        // Scan Human Village for gate buildings
        for (Gate gate : GATES) {
            if (!unlockedGates.contains(gate.unlockKey())) {
                if (isGateBuildingBuilt(gate.buildingKey())) {
                    unlockGate(gate);
                }
            }
        }
    }
    
    /**
     * Checks if a gate building is built in Human Village.
     */
    private boolean isGateBuildingBuilt(String buildingKey) {
        // Scan Human Village settlement for building
        // Using reflection to access Settlement's built rooms
        try {
            var humanVillage = getHumanVillage();
            if (humanVillage == null) return false;
            
            var builtRooms = getBuiltRooms(humanVillage);
            for (Object room : builtRooms) {
                String roomKey = getRoomKey(room);
                if (buildingKey.equalsIgnoreCase(roomKey)) {
                    return true;
                }
            }
        } catch (Exception e) {
            System.err.println("[GateManager] Error scanning for building: " + buildingKey);
        }
        return false;
    }
    
    /**
     * Unlocks a gate and notifies player.
     */
    private void unlockGate(Gate gate) {
        unlockedGates.add(gate.unlockKey());
        
        // Notify player
        notifyPlayer(gate);
        
        // Set boost flag for room requirements
        setBoostFlag(gate.unlockKey(), true);
        
        // Log
        System.out.println("[GateManager] Gate unlocked: " + gate.description());
    }
    
    private void notifyPlayer(Gate gate) {
        try {
            var uiApi = com.github.argon.sos.mod.sdk.api.GameApis.ui();
            if (com.github.argon.sos.mod.sdk.api.GameApis.ui() != null) {
                com.github.argon.sos.mod.sdk.api.GameUiApi uiApi = com.github.argon.sos.mod.sdk.api.GameApis.ui();
                uiApi.showNotification(
                    "Neue Funktion freigeschaltet!",
                    "Durch Bau im Menschendorf: " + gate.description(),
                    com.github.argon.sos.mod.sdk.api.GameUiApi.NotificationType.SUCCESS,
                    10.0
                );
            }
        } catch (Exception e) {
            // Ignore UI errors
        }
    }
    
    private void setBoostFlag(String key, boolean value) {
        try {
            var statsApi = com.github.argon.sos.mod.sdk.api.GameApis.stats();
            var boostable = com.github.argon.sos.mod.sdk.api.GameApis.stats().getBoostable(gateKey);
            if (boostable.isPresent()) {
                boostable.get().setValue(value ? 1.0 : 0.0);
            }
        } catch (Exception e) {
            // Ignore
        }
    }
    
    private Object getHumanVillage() {
        // Get Human Village settlement via reflection
        try {
            var player = com.github.argon.sos.mod.sdk.api.GameApis.faction().getPlayer();
            if (player == null) return null;
            
            var world = com.syxcraft.undead.util.ReflectionUtil.getStaticFieldValue(
                Class.forName("world.WORLD"), "instance");
            if (world == null) return null;
            
            var regions = com.syxcraft.undead.util.ReflectionUtil.getFieldValue(world, "regions");
            if (regions instanceof java.util.List) {
                for (Object region : (java.util.List<?>) regions) {
                    if (hasHumanVillageMarker(region)) {
                        return getSettlementFromRegion(region);
                    }
                }
            }
        } catch (Exception e) {
            // Silent
        }
        return null;
    }
    
    private boolean hasHumanVillageMarker(Object region) {
        try {
            var field = com.syxcraft.undead.util.ReflectionUtil.getDeclaredField("humanVillage", region.getClass());
            field.setAccessible(true);
            return (Boolean) field.get(region);
        } catch (Exception e) {
            return false;
        }
    }
    
    private Object getSettlementFromRegion(Object region) {
        try {
            var field = com.syxcraft.undead.util.ReflectionUtil.getDeclaredField("settlement", region.getClass());
            field.setAccessible(true);
            return field.get(region);
        } catch (Exception e) {
            return null;
        }
    }
    
    private java.util.List<?> getBuiltRooms(Object settlement) {
        try {
            var method = com.syxcraft.undead.util.ReflectionUtil.getDeclaredMethod("getBuiltRooms", settlement.getClass());
            method.setAccessible(true);
            return (java.util.List<?>) method.invoke(settlement);
        } catch (Exception e) {
            return java.util.Collections.emptyList();
        }
    }
    
    private String getRoomKey(Object room) {
        try {
            var field = com.syxcraft.undead.util.ReflectionUtil.getDeclaredField("key", room.getClass());
            field.setAccessible(true);
            return (String) field.get(room);
        } catch (Exception e) {
            return null;
        }
    }
    
    public boolean isUnlocked(String unlockKey) {
        return unlockedGates.contains(unlockKey);
    }
    
    public java.util.Set<String> getUnlockedGates() {
        return java.util.Collections.unmodifiableSet(unlockedGates);
    }
    
    // Save/Load
    public void onGameSaved(java.nio.file.Path path, snake2d.util.file.FilePutter putter) {
        putter.mark(1)
            .chars("COUNT").chars(String.valueOf(unlockedGates.size()));
        
        int i = 0;
        for (String key : unlockedGates) {
            putter.chars("GATE_" + i).chars(key);
            i++;
        }
    }
    
    public void onGameLoaded(snake2d.util.file.FileGetter getter) {
        getter.check();
        int count = Integer.parseInt(getter.chars("COUNT"));
        unlockedGates.clear();
        for (int i = 0; i < count; i++) {
            unlockedGates.add(getter.chars("GATE_" + i));
        }
    }
    
    // Gate record
    private record Gate(String buildingKey, String unlockKey, String description) {
        public String buildingKey() { return buildingKey; }
        public String unlockKey() { return unlockKey; }
        public String description() { return description; }
    }
}