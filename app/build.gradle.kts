import com.android.build.api.variant.ApplicationVariant
import com.android.build.api.variant.SourceDirectories

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

// ── Path to root prebuilt Python ──────────────────────────────────────────
val pythonPrebuiltsDir = file("${rootProject.projectDir}/python-prebuilts")
val pythonVersion = "3.14"

android {
    namespace = "com.example.stratum_android_py_3_14"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.example.stratum_android_py_3_14"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        ndk {
            abiFilters.addAll(listOf("arm64-v8a", "x86_64"))
        }

        externalNativeBuild {
            cmake {
                cppFlags("-std=c++17")
                arguments(
                    "-DANDROID_STL=c++_shared",
                    "-DPYTHON_VERSION=$pythonVersion",
                    "-DPYTHON_PREBUILTS_ROOT=${pythonPrebuiltsDir.absolutePath}",
                    "-DANDROID_SUPPORT_FLEXIBLE_PAGE_SIZES=ON"
                )
            }
        }

        androidResources {
            noCompress.add("gz")
            // Prevent asset packing from ignoring python files starting with underscore
            ignoreAssetsPattern = "!.svn:!.git:!.ds_store:!*.scc:.*:!CVS:!thumbs.db:!picasa.ini:!*~"
        }
    }

    buildTypes {
        debug {
            // Generates BuildConfig.DEBUG for fast hot-syncing
            buildConfigField("boolean", "IS_DEBUG", "true")
        }
        release {
            isMinifyEnabled = false
            buildConfigField("boolean", "IS_DEBUG", "false")
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    buildFeatures {
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    externalNativeBuild {
        cmake {
            path = file("src/main/cpp/CMakeLists.txt")
            version = "3.22.1"
        }
    }

    sourceSets {
        getByName("main") {
            // Keep your Stratum libstratum.so if present
            jniLibs.srcDirs("src/main/jniLibs")
        }
    }
}

// ── Automated packaging of Python stdlib and JNI libs ─────────────────────
androidComponents.onVariants { variant ->
    val pyFolder = "python$pythonVersion"

    // 1. Pack python stdlib and ABI-specific lib-dynload into Assets automatically
    generateTask(variant, variant.sources.assets!!) {
        // Pure Python stdlib (architecture-independent)
        into("python/stdlib") {
            val stdlibSrc = file("$pythonPrebuiltsDir/arm64-v8a/prefix/lib/$pyFolder")
            if (stdlibSrc.exists()) {
                from(stdlibSrc) {
                    exclude("**/__pycache__/**")
                    exclude("**/test/**")
                    exclude("**/tests/**")
                    exclude("**/idlelib/**")
                    exclude("**/tkinter/**")
                    exclude("**/lib-dynload/**") // Exclude architecture-specific binaries from shared stdlib
                }
            }
            duplicatesStrategy = DuplicatesStrategy.EXCLUDE
        }

        // Separate lib-dynload (zlib, math, etc.) for each architecture
        for (abi in listOf("arm64-v8a", "x86_64")) {
            val dynloadSrc = file("$pythonPrebuiltsDir/$abi/prefix/lib/$pyFolder/lib-dynload")
            if (dynloadSrc.exists()) {
                into("python/lib-dynload/$abi") {
                    from(dynloadSrc) {
                        exclude("**/__pycache__/**")
                    }
                }
            }
        }
    }

    // 2. Pack .so files into APK lib/<abi>/ automatically
    generateTask(variant, variant.sources.jniLibs!!) {
        for (abi in listOf("arm64-v8a", "x86_64")) {
            val libDir = file("$pythonPrebuiltsDir/$abi/prefix/lib")
            if (libDir.exists()) {
                into(abi) {
                    from(libDir)
                    // Include main python engine and companion builds
                    include("libpython*.so")
                    include("lib*_python.so")
                    include("libsqlite3*.so")
                    include("libcrypto*.so")
                    include("libssl*.so")
                    include("libz*.so")
                    // Exclude invalid Windows symlink files and directories
                    exclude("*.so.0")
                    exclude("pkgconfig/**")
                    exclude("engines-3/**")
                    exclude("ossl-modules/**")
                }
            }
        }
    }
}

fun generateTask(
    variant: ApplicationVariant,
    directories: SourceDirectories,
    configure: GenerateTask.() -> Unit
) {
    val taskName = "generate" +
            listOf(variant.name, "Python", directories.name)
                .map { it.replaceFirstChar(Char::uppercase) }
                .joinToString("")

    directories.addGeneratedSourceDirectory(
        tasks.register<GenerateTask>(taskName) {
            into(outputDir)
            configure()
        },
        GenerateTask::outputDir
    )
}

abstract class GenerateTask : Sync() {
    @get:OutputDirectory
    abstract val outputDir: DirectoryProperty
}

dependencies {
    implementation(project(":stratum-runtime"))
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.material)
    implementation(libs.androidx.activity)
    implementation(libs.androidx.constraintlayout)

    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
}