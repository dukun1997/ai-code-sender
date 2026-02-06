plugins {
    id("org.jetbrains.intellij.platform") version "2.11.0"
    kotlin("jvm") version "2.2.20"
}

group = "com.dukun"
version = "0.1.1"

val localIdePath = providers.gradleProperty("localIdePath").orNull

kotlin {
    jvmToolchain(21)
}

repositories {
    mavenCentral()
    intellijPlatform {
        defaultRepositories()
    }
}

dependencies {
    intellijPlatform {
        if (localIdePath.isNullOrBlank()) {
            intellijIdeaCommunity("2025.2")
        } else {
            local(localIdePath)
        }
        bundledPlugin("com.intellij.java")
        bundledPlugin("org.jetbrains.plugins.terminal")
    }
}

intellijPlatform {
    pluginConfiguration {
        ideaVersion {
            sinceBuild.set("253")
        }
    }
}
