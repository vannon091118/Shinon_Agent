# Mod Structure Concept — SyxCraft Undead Overhaul

## Maven Project Structure

```
syxcraft-undead/
├── pom.xml                           # Maven Build Config
├── package.json                      # Node Validator (SyxCode)
├── syxcode.config.json              # Validator Config
├── local.properties.example         # Game Paths Template
├── .gitignore
├── README.md
├── CHANGELOG.md
├── src/
│   ├── main/
│   │   ├── java/
│   │   │   └── com/
│   │   │       └── syxcraft/
│   │   │           └── undead/
│   │   │               ├── UndeadScript.java           # Main SCRIPT Entry Point
│   │   │               ├── state/
│   │   │               │   ├── UndeadState.java        # State Manager
│   │   │               │   └── HumanFarmState.java     # Farm State
│   │   │               ├── logic/
│   │   │               │   ├── HumanFarmManager.java   # Farm Production Logic
│   │   │               │   ├── ConversionManager.java  # Human→Undead Conversion
│   │   │               │   ├── OrcTradeManager.java    # Orc Slave Trade
│   │   │               │   └── TechUnlockManager.java  # Tech Feature Flags
│   │   │               ├── events/
│   │   │               │   └── UndeadEventBuilder.java # Runtime Event Creation
│   │   │               └── util/
│   │   │                   └── UndeadUtils.java        # Helpers: Race Checks, Resource Access
│   │   └── resources/
│   │       └── mod-files/                    # Data Files (werden nach V71/ kopiert)
│   │           ├── _Info.txt
│   │           ├── init/
│   │           │   ├── race/UNDEAD.txt
│   │           │   ├── resource/supply/CAPTIVE_HUMAN.txt
│   │           │   ├── room/
│   │           │   │   ├── HUMAN_PENS.txt
│   │           │   │   └── NECROPOLIS.txt
│   │           │   ├── tech/NECROMANCY_HUMAN_FARM.txt
│   │           │   ├── event/
│   │           │   │   ├── UNDEAD_CONVERSION.txt
│   │           │   │   ├── HUMAN_FARM_ESTABLISH.txt
│   │           │   │   ├── ORC_SLAVE_TRADE.txt
│   │           │   │   └── NECROMANCY_POLICY.txt
│   │           │   └── world/building/WORLD_HUMAN_FARM.txt
│   │           └── script/_src/              # Source für Workshop Transparenz
└── └── test/
        └── java/...                          # Unit Tests
```

---

## pom.xml — Key Configuration

```xml
<project>
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.syxcraft</groupId>
    <artifactId>syxcraft-undead</artifactId>
    <version>0.1.0</version>
    <packaging>jar</packaging>

    <properties>
        <maven.compiler.source>21</maven.compiler.source>
        <maven.compiler.target>21</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        
        <game.version.major>71</game.version.major>
        <game.version.minor>44</game.version.minor>
        <game.jar.name>SongsOfSyx.jar</game.jar.name>
        <game.install.directory>${user.home}/.steam/steam/steamapps/common/Songs of Syx</game.install.directory>
        
        <mod.sdk.version>0.1.5</mod.sdk.version>
    </properties>

    <profiles>
        <profile>
            <id>mod-sdk</id>
            <dependencies>
                <dependency>
                    <groupId>io.github.4rg0n</groupId>
                    <artifactId>sos-mod-sdk</artifactId>
                    <version>${mod.sdk.version}</version>
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
                <excludes><exclude>**/_src/**</exclude></excludes>
            </resource>
        </resources>

        <plugins>
            <!-- Game JAR als Dependency installieren -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-install-plugin</artifactId>
                <version>3.1.1</version>
                <executions>
                    <execution>
                        <id>install-game-jar</id>
                        <phase>validate</phase>
                        <goals><goal>install-file</goal></goals>
                        <configuration>
                            <groupId>com.songsofsyx</groupId>
                            <artifactId>songsofsyx</artifactId>
                            <version>${game.version.major}.${game.version.minor}</version>
                            <packaging>jar</packaging>
                            <file>${game.install.directory}/${game.jar.name}</file>
                            <generatePom>true</generatePom>
                        </configuration>
                    </execution>
                </executions>
            </plugin>

            <!-- Fat JAR (ohne Game Classes) -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-shade-plugin</artifactId>
                <version>3.6.0</version>
                <executions>
                    <execution>
                        <phase>package</phase>
                        <goals><goal>shade</goal></goals>
                        <configuration>
                            <artifactSet>
                                <excludes><exclude>com.songsofsyx:*</exclude></excludes>
                            </artifactSet>
                            <createDependencyReducedPom>false</createDependencyReducedPom>
                        </configuration>
                    </execution>
                </executions>
            </plugin>

            <!-- Source JAR für Workshop -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-source-plugin</artifactId>
                <version>3.2.1</version>
                <executions>
                    <execution>
                        <id>attach-sources</id>
                        <phase>package</phase>
                        <goals><goal>jar-no-fork</goal></goals>
                    </execution>
                </executions>
            </plugin>

            <!-- Mod Files kopieren nach Build Output -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-resources-plugin</artifactId>
                <version>3.2.0</version>
                <executions>
                    <execution>
                        <id>copy-mod-files</id>
                        <phase>package</phase>
                        <goals><goal>copy-resources</goal></goals>
                        <configuration>
                            <outputDirectory>${project.build.directory}/out/${project.artifactId}/V${game.version.major}</outputDirectory>
                            <includeEmptyDirs>true</includeEmptyDirs>
                            <overwrite>true</overwrite>
                            <resources>
                                <resource>
                                    <directory>src/main/resources/mod-files</directory>
                                    <excludes><exclude>**/_src/**</exclude></excludes>
                                </resource>
                            </resources>
                        </configuration>
                    </execution>
                    <execution>
                        <id>copy-mod-jar</id>
                        <phase>package</phase>
                        <goals><goal>copy-resources</goal></goals>
                        <configuration>
                            <outputDirectory>${project.build.directory}/out/${project.artifactId}/V${game.version.major}/script</outputDirectory>
                            <resources>
                                <resource>
                                    <directory>${project.build.directory}</directory>
                                    <includes><include>${project.build.finalName}.jar</include></includes>
                                </resource>
                            </resources>
                        </configuration>
                    </execution>
                    <execution>
                        <id>copy-sources</id>
                        <phase>package</phase>
                        <goals><goal>copy-resources</goal></goals>
                        <configuration>
                            <outputDirectory>${project.build.directory}/out/${project.artifactId}/V${game.version.major}/script/_src</outputDirectory>
                            <resources>
                                <resource>
                                    <directory>${project.build.directory}</directory>
                                    <includes><include>${project.build.finalName}-sources.jar</include></includes>
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

## local.properties.example

```properties
# Game Installation Paths (anpassen!)
game.install.directory=/home/user/.steam/steam/steamapps/common/Songs of Syx
game.workshop.directory=/home/user/.steam/steam/steamapps/workshop/content/1162750
game.mod.directory=/home/user/.local/share/songsofsyx/mods
game.mod.uploader.directory=/home/user/.local/share/songsofsyx/mods-uploader
```

---

## package.json (SyxCode Validator)

```json
{
  "name": "syxcraft-undead",
  "version": "0.1.0",
  "description": "Validation and development tools for SyxCraft Undead Overhaul",
  "main": "index.js",
  "scripts": {
    "test": "node tools/core/validator.js",
    "sync:version": "node tools/core/validator.js --sync-version",
    "signatures:update": "node tools/core/signatures_updater.js"
  },
  "devDependencies": {
    "diff": "^5.2.0",
    "xmldom": "^0.6.0"
  }
}
```

---

## syxcode.config.json

```json
{
  "paths": {
    "init_root": "target/out/${project.artifactId}/V${game.version.major}/data/init",
    "script_jar": "target/out/${project.artifactId}/V${game.version.major}/script/${project.artifactId}.jar"
  },
  "schemas": {
    "race": "tools/schemas/race.schema.json",
    "resource": "tools/schemas/resource.schema.json",
    "tech": "tools/schemas/tech.schema.json",
    "room": "tools/schemas/room.schema.json",
    "world_building": "tools/schemas/world_building.schema.json",
    "event": "tools/schemas/event.schema.json"
  }
}
```

---

## Build & Deploy Commands

```bash
# 1. Game JAR in lokalem Maven Repo installieren (einmalig)
mvn validate -Dgame.install.directory="/path/to/Songs of Syx"

# 2. Development Build (nur Data + Script JAR)
mvn clean package

# 3. Build mit Mod SDK Features (GameEventsApi, GameFactionApi, etc.)
mvn clean package -Pmod-sdk

# 4. Output Structure nach Build:
target/out/syxcraft-undead/
└── V71/
    ├── _Info.txt
    ├── data/init/...           # Alle .txt Data Files
    └── script/
        ├── syxcraft-undead.jar # Für Spiel geladen
        └── _src/
            └── syxcraft-undead-sources.jar

# 5. Installation in Spiel:
cp -r target/out/syxcraft-undead/V71 ~/.local/share/songsofsyx/mods/SyxCraft-Undead/

# 6. Workshop Upload (via Mod Uploader Tool oder Steam CMD)
```

---

## Integration in SyxCraft Main Repo

### Option A: Git Submodule (Empfohlen)
```bash
# In SyxCraft Main Repo
git submodule add https://github.com/vannon091118/syxcraft-undead.git modules/undead
# Build Script erweitern: mvn -f modules/undead/pom.xml package
```

### Option B: Separates Repo, Shared Validator
- SyxCraft Validator (`package.json` scripts) prüft auch Submodule
- Version Sync via Git Tags

---

## Workshop Upload Structure

```
WorkshopContent/
├── _Info.txt
├── V71/
│   ├── data/init/...
│   └── script/
│       ├── syxcraft-undead.jar
│       └── _src/
│           └── syxcraft-undead-sources.jar
```

**Wichtig:** `_src` Ordner mit Source JAR ist **Pflicht** für Workshop Mods (Transparenz).