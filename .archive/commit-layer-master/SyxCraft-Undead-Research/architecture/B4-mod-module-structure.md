# B4 — Mod Module Structure Analysis

> **Engine Version:** V71.44
> **Research Date:** 2026-07-14
> **Status:** Complete — Architecture Decision Documented

---

## 1. The Structure Question

**Wie soll das Repo intern strukturiert werden?**

| Option A — Ein Mod, alle Rassen | Option B — Ein Mod pro Rasse |
|----------------------------------|------------------------------|
| `mods/SyxCraft/` | `mods/SyxCraft-Undead/` |
| `└── V71/` | `mods/SyxCraft-Orc/` |
| `    ├── data/init/race/` (alle 4) | `mods/SyxCraft-Human/` |
| `    ├── data/init/room/` (alle) | `mods/SyxCraft-NightElf/` |
| `    └── script/syxcraft.jar` | |

---

## 2. Detailed Comparison

### Option A — Single Mod (SyxCraft)

**Structure:**
```
mods/SyxCraft/
├── _Info.txt
└── V71/
    ├── data/init/
    │   ├── race/
    │   │   ├── HUMAN.txt
    │   │   ├── ORC.txt
    │   │   ├── UNDEAD.txt
    │   │   └── NIGHT_ELF.txt
    │   ├── room/
    │   │   ├── HUMAN_BARRACKS.txt
    │   │   ├── ORC_SLAVE_PEN.txt
    │   │   ├── UNDEAD_NECROPOLIS.txt
    │   │   └── NIGHT_ELF_MOONWELL.txt
    │   ├── tech/
    │   │   ├── HUMAN_CIVICS.txt
    │   │   ├── ORC_RAIDING.txt
    │   │   ├── UNDEAD_NECROMANCY.txt
    │   │   └── NIGHT_ELF_DRUIDISM.txt
    │   ├── law/
    │   │   ├── UNDEAD_SLAVERY.txt
    │   │   ├── ORC_SLAVERY.txt
    │   │   └── NIGHT_ELF_PROTECTION.txt
    │   ├── event/
    │   │   ├── UNDEAD_CONVERSION.txt
    │   │   ├── ORC_SLAVE_RAID.txt
    │   │   ├── HUMAN_IMMIGRATION.txt
    │   │   └── NIGHT_ELF_MOON_FADE.txt
    │   └── diplomacy/
    │       └── REQUEST_SLAVE_TRADE.txt
    └── script/
        └── syxcraft.jar
            └── com/syxcraft/
                ├── core/          # Core Script + Bus
                ├── undead/        # Undead Module
                ├── orc/           # Orc Module
                ├── human/         # Human Module
                └── nightelf/      # Night Elf Module
```

**Workshop Upload:** 1 Mod, 1 Upload, 1 Version

**Dependencies:** Keine internen Dependencies

**Load Order:** Egal — 1 Mod

---

### Option B — Separate Mods

**Structure:**
```
mods/
├── SyxCraft-Undead/
│   ├── _Info.txt
│   └── V71/
│       ├── data/init/race/UNDEAD.txt
│       ├── data/init/room/UNDEAD_NECROPOLIS.txt
│       ├── data/init/tech/UNDEAD_NECROMANCY.txt
│       ├── data/init/law/UNDEAD_SLAVERY.txt
│       ├── data/init/event/UNDEAD_CONVERSION.txt
│       └── script/undead.jar
│           └── com/syxcraft/undead/
├── SyxCraft-Orc/
│   ├── _Info.txt
│   └── V71/
│       ├── data/init/race/ORC.txt
│       ├── data/init/room/ORC_SLAVE_PEN.txt
│       ├── data/init/tech/ORC_RAIDING.txt
│       ├── data/init/law/ORC_SLAVERY.txt
│       ├── data/init/event/ORC_SLAVE_RAID.txt
│       └── script/orc.jar
│           └── com/syxcraft/orc/
├── SyxCraft-Human/
│   ├── _Info.txt
│   └── V71/
│       ├── data/init/race/HUMAN.txt
│       ├── data/init/tech/HUMAN_CIVICS.txt
│       └── script/human.jar
└── SyxCraft-NightElf/
    ├── _Info.txt
    └── V71/
        ├── data/init/race/NIGHT_ELF.txt
        ├── data/init/tech/NIGHT_ELF_DRUIDISM.txt
        └── script/nightelf.jar
```

**Workshop Upload:** 4 Mods, 4 Uploads, 4 Versionen

**Dependencies:** 
- `SyxCraft-Orc` requires `SyxCraft-Undead` (für Slave Trade)
- `SyxCraft-Undead` requires `SyxCraft-Orc` (für Slave Source)
- **Circular Dependency Problem!**

**Load Order:** Kritisch — Wer lädt zuerst?

---

## 3. Criteria Evaluation

| Kriterium | Option A (Single) | Option B (Separate) | Gewichtung |
|-----------|-------------------|---------------------|------------|
| **Agent-Parallelarbeit** | ❌ Konflikte | ✅ Isoliert | **KRITISCH** |
| **Build System** | 1 Maven Module | 4 Maven Modules | Hoch |
| **Workshop Upload** | 1 Upload | 4 Uploads | Mittel |
| **Dependency Hell** | Keine | **Zirkulär!** | **KRITISCH** |
| **Load Order** | Egal | Kritisch | Hoch |
| **Testing Isolation** | Schwer | Einfach | Hoch |
| **Version Sync** | Automatisch | Manueller Sync | Mittel |
| **Hot Reload** | Ganzes Mod | Einzelnes Modul | Niedrig |
| **Cross-Race Features** | Einfach (Core Bus) | Schwer (Mod API) | **KRITISCH** |
| **Future Rassen** | Einfach addieren | Neues Mod erstellen | Mittel |

---

## 4. Circular Dependency Analysis (Option B)

```
SyxCraft-Undead ──────► needs Orc Slaves ──────► SyxCraft-Orc
      ▲                                              │
      │                                              │
      └──── needs Undead Conversion ◄───────────────┘
      
      Slave Trade Event needs BOTH mods loaded
      Diplomatic Action REQUEST_SLAVE_TRADE needs both
      
      Solution: Shared Library Mod?
      mods/SyxCraft-Core/  (Shared constants, events, bus)
           ▲              ▲
           │              │
    SyxCraft-Undead  SyxCraft-Orc
    
      But then: 3 Mods, still load order issues
```

---

## 5. Recommendation: **Option A — Single Mod**

### Begründung

1. **Keine Circular Dependencies** — Cross-Race Features (Slave Trade, Diplomacy) funktionieren nativ
2. **Agent-Parallelarbeit** — Durch Package-Isolation (`com.syxcraft.undead`, `com.syxcraft.orc`, etc.) keine Merge-Konflikte
3. **Single Workshop Upload** — 1 Mod, 1 Version, 1 Upload
4. **Single Build** — 1 Maven Module, 1 JAR
5. **Core Bus Pattern** — Typsichere Cross-Race Communication ohne Mod-API
6. **Load Order** — Egal, nur 1 Mod
7. **Testing** — Core mocken, Module isoliert testen
7. **Extensibility** — Neue Rassen = neue Packages im gleichen Mod

---

## 6. Package Structure für Single Mod (Final)

```
src/main/java/com/syxcraft/
├── core/                          # Agent 0 — Architecture
│   ├── SyxCraftCoreScript.java    # SCRIPT entry point
│   ├── SyxCraftCoreInstance.java  # SCRIPT_INSTANCE
│   ├── CoreBus.java               # Event Bus
│   ├── CoreEvent.java             # Base Event
│   ├── CoreStateManager.java      # Shared State (Save/Load)
│   ├── RaceModule.java            # Abstract Module Base
│   └── constant/
│       └── SyxCraftConstants.java # Shared Constants
├── undead/                        # Agent 1 — Undead
│   ├── UndeadModule.java
│   ├── manager/
│   │   ├── GhostManager.java
│   │   ├── ConversionManager.java
│   │   ├── GateManager.java
│   │   └── HumanFarmManager.java
│   ├── state/
│   │   ├── GhostState.java
│   │   ├── ConversionState.java
│   │   └── HumanFarmState.java
│   └── event/
│       ├── RebellionEvent.java
│       └── ConversionEvent.java
├── orc/                           # Agent 2 — Orc
│   ├── OrcModule.java
│   ├── manager/
│   │   ├── RaidManager.java
│   │   └── SlaveTradeManager.java
│   └── event/
│       └── SlaveRaidEvent.java
├── human/                         # Agent 3 — Human
│   ├── HumanModule.java
│   └── manager/
│       └── ImmigrationManager.java
├── nightelf/                      # Agent 4 — Night Elf
│   ├── NightElfModule.java
│   └── manager/
│       └── StealthManager.java
└── util/                          # Shared Utilities
    ├── ReflectionUtil.java
    └── MathUtil.java
```

---

## 7. Maven Build für Single Mod

```xml
<!-- pom.xml für SyxCraft (Single Mod) -->
<project>
    <groupId>com.syxcraft</groupId>
    <artifactId>syxcraft</artifactId>
    <version>0.1.0</version>
    <packaging>jar</packaging>
    
    <properties>
        <maven.compiler.source>21</maven.compiler.source>
        <maven.compiler.target>21</maven.compiler.target>
        <game.version.major>71</game.version.major>
        <game.version.minor>44</game.version.minor>
    </properties>
    
    <profiles>
        <profile>
            <id>mod-sdk</id>
            <dependencies>
                <dependency>
                    <groupId>io.github.4rg0n</groupId>
                    <artifactId>sos-mod-sdk</artifactId>
                    <version>0.1.5</version>
                </dependency>
            </dependencies>
            <repositories>
                <repository>
                    <id>github-4rg0n</id>
                    <url>https://maven.pkg.github.com/4rg0n/Songs-of-Syx-Mod-SDK</url>
                </repository>
            </repositories>
        </profile>
    </profiles>
    
    <dependencies>
        <dependency>
            <groupId>com.songsofsyx</groupId>
            <artifactId>songsofsyx</artifactId>
            <version>${game.version.major}.${game.version.minor}</version>
            <scope>provided</scope>
        </dependency>
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <version>1.18.42</version>
            <scope>provided</scope>
        </dependency>
    </dependencies>
    
    <build>
        <finalName>${project.artifactId}</finalName>
        
        <resources>
            <resource>
                <directory>src/main/resources/mod-files</directory>
                <filtering>true</filtering>
                <excludes>
                    <exclude>**/_src/**</exclude>
                </excludes>
            </resource>
        </resources>
        
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-install-plugin</artifactId>
                <version>3.1.1</version>
                <executions>
                    <execution>
                        <id>install-game-jar</id>
                        <phase>validate</phase>
                        <goals>
                            <goal>install-file</goal>
                        </goals>
                        <configuration>
                            <groupId>com.songsofsyx</groupId>
                            <artifactId>songsofsyx</artifactId>
                            <version>${game.version.major}.${game.version.minor}</version>
                            <packaging>jar</packaging>
                            <file>${game.install.directory}/SongsOfSyx.jar</file>
                            <generatePom>true</generatePom>
                        </configuration>
                    </execution>
                </executions>
            </plugin>
            
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-shade-plugin</artifactId>
                <version>3.6.0</version>
                <executions>
                    <execution>
                        <phase>package</phase>
                        <goals>
                            <goal>shade</goal>
                        </goals>
                        <configuration>
                            <artifactSet>
                                <excludes>
                                    <exclude>com.songsofsyx:*</exclude>
                                </excludes>
                            </artifactSet>
                            <createDependencyReducedPom>false</createDependencyReducedPom>
                        </configuration>
                    </execution>
                </executions>
            </plugin>
            
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-resources-plugin</artifactId>
                <version>3.2.0</version>
                <executions>
                    <execution>
                        <id>copy-mod-files</id>
                        <phase>package</phase>
                        <goals>
                            <goal>copy-resources</goal>
                        </goals>
                        <configuration>
                            <outputDirectory>${project.build.directory}/out/${project.artifactId}/V${game.version.major}</outputDirectory>
                            <includeEmptyDirs>true</includeEmptyDirs>
                            <overwrite>true</overwrite>
                            <resources>
                                <resource>
                                    <directory>src/main/resources/mod-files</directory>
                                    <excludes>
                                        <exclude>**/_src/**</exclude>
                                    </excludes>
                                </resource>
                            </resources>
                        </configuration>
                    </execution>
                    <execution>
                        <id>copy-mod-jar</id>
                        <phase>package</phase>
                        <goals>
                            <goal>copy-resources</goal>
                        </goals>
                        <configuration>
                            <outputDirectory>${project.build.directory}/out/${project.artifactId}/V${game.version.major}/script</outputDirectory>
                            <resources>
                                <resource>
                                    <directory>${project.build.directory}</directory>
                                    <includes>
                                        <include>${project.build.finalName}.jar</include>
                                    </includes>
                                </resource>
                            </resources>
                        </configuration>
                    </execution>
                </executions>
            </plugin>
        </plugins>
    </build>
</project>
```

---

## 8. Workshop Structure (Single Mod)

```
mods/SyxCraft/
├── _Info.txt
└── V71/
    ├── data/init/
    │   ├── race/
    │   │   ├── HUMAN.txt
    │   │   ├── ORC.txt
    │   │   ├── UNDEAD.txt
    │   │   └── NIGHT_ELF.txt
    │   ├── room/
    │   │   ├── UNDEAD_NECROPOLIS.txt
    │   │   ├── ORC_SLAVE_PEN.txt
    │   │   ├── NIGHT_ELF_MOONWELL.txt
    │   │   └── ...
    │   ├── tech/
    │   │   ├── UNDEAD_NECROMANCY.txt
    │   │   ├── ORC_RAIDING.txt
    │   │   ├── HUMAN_CIVICS.txt
    │   │   └── NIGHT_ELF_DRUIDISM.txt
    │   ├── law/
    │   │   ├── UNDEAD_SLAVERY.txt
    │   │   ├── UNDEAD_CONVERSION.txt
    │   │   ├── HUMAN_FARM_MANAGEMENT.txt
    │   │   ├── ORC_SLAVERY.txt
    │   │   └── ORC_SLAVE_TRADE.txt
    │   ├── event/
    │   │   ├── UNDEAD_CONVERSION.txt
    │   │   ├── ORC_SLAVE_RAID.txt
    │   │   ├── ORC_SLAVE_TRADE.txt
    │   │   ├── HUMAN_FARM_ESTABLISH.txt
    │   │   ├── INDEPENDENCE_ATTEMPT.txt
    │   │   ├── BLIGHT_CLEANSE.txt
    │   │   ├── SENTINEL_PATROL.txt
    │   │   └── MOON_FADE.txt
    │   ├── diplomacy/
    │   │   └── REQUEST_SLAVE_TRADE.txt
    │   └── world/building/
    │       └── WORLD_HUMAN_FARM.txt
    ├── script/
    │   ├── syxcraft.jar          # Compiled Script
    │   └── _src/
    │       └── syxcraft-sources.jar
    └── res/                       # Sprites, Icons, Sounds
        └── ...
```

---

## 9. UNVERIFIED — Requires Testing

| Question | Status | Priority |
|----------|--------|----------|
| Lädt SoS alle Data-Files aus EINEM Mod korrekt? | **UNVERIFIED** | CRITICAL |
| Funktioniert `_ignoreVanilla: true` für 4 Rassen in 1 Mod? | **UNVERIFIED** | CRITICAL |
| Werden alle Events aus 1 Mod geladen? | **UNVERIFIED** | HIGH |
| Konflikte bei gleichen Room/Tech Keys? | **UNVERIFIED** | HIGH |
| Maven Shade Plugin packt Script korrekt? | **UNVERIFIED** | MEDIUM |

---

## 10. Decision Record

**DECISION:** **Option A — Single Mod (SyxCraft)**

**RATIONALE:**
- Eliminates Circular Dependencies completely
- Enables Agent Parallel Work via Package Isolation
- Single Workshop Upload, Single Version
- Core Bus Pattern enables clean Cross-Race Communication
- Single Build, Single Load Order, Single Test Suite

**CONSEQUENCES:**
- Core must be stable first (blocking for all agents)
- Package Discipline strictly enforced (Code Review)
- Single JAR — if one race breaks, all break (mitigated by Testing)
- Large JAR but manageable (~500KB)

---

*End of B4 — Mod Module Structure Analysis*
*Decision: Single Mod Architecture with Core + Race Modules*