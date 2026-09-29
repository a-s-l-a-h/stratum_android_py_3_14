package com.example.stratum_android_py_3_14

import android.content.Context
import android.os.Build
import android.os.Bundle
import android.system.Os
import android.util.Log
import com.stratum.runtime.StratumActivity
import com.stratum.runtime.StratumBootstrap
import java.io.File
import java.io.FileOutputStream

class MainActivity : StratumActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        val internalPythonDir = File(filesDir, "python")
        if (!internalPythonDir.exists()) {
            internalPythonDir.mkdirs()
        }

        // ── 1. Smart Asset Extraction ─────────────────────────────────────
        syncPythonAssets(this, internalPythonDir)

        // ── 2. Link libstratum.so -> stratum.so in Python search path ─────
        val stratumSoSource = File(applicationInfo.nativeLibraryDir, "libstratum.so")
        val stratumSoTarget = File(internalPythonDir, "stratum.so")

        try {
            stratumSoTarget.delete()
        } catch (_: Exception) {}

        if (stratumSoSource.exists()) {
            try {
                Os.symlink(stratumSoSource.absolutePath, stratumSoTarget.absolutePath)
            } catch (e: Exception) {
                try {
                    stratumSoSource.copyTo(stratumSoTarget, overwrite = true)
                } catch (copyEx: Exception) {
                    Log.e("MainActivity", "Failed to link/copy stratum.so", copyEx)
                }
            }
        } else {
            Log.w("MainActivity", "libstratum.so not found at: ${stratumSoSource.absolutePath}")
        }

        // ── 3. Start CPython interpreter ──────────────────────────────────
        if (!PythonHost.initPython(internalPythonDir.absolutePath)) {
            throw RuntimeException("[MainActivity] Failed to initialize Python runtime")
        }

        // ── 4. Mark Bootstrap ready ────────────────────────────────────────
        StratumBootstrap.markReady()

        // ── 5. Run StratumActivity lifecycle
        super.onCreate(savedInstanceState)
    }

    override fun onImportMain(): Boolean = PythonHost.importModule("main")
    override fun onBackPressedPy(): Boolean = PythonHost.onBackPressed()

    /**
     * Synchronizes Python assets to internal app storage.
     * - Stdlib is only extracted once per APK update (based on lastUpdateTime).
     * - In DEBUG mode, user scripts (like main.py) are ALWAYS overwritten on launch,
     *   allowing immediate code updates without uninstalling the app!
     */
    private fun syncPythonAssets(context: Context, outDir: File) {
        val packageInfo = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            context.packageManager.getPackageInfo(context.packageName, android.content.pm.PackageManager.PackageInfoFlags.of(0))
        } else {
            @Suppress("DEPRECATION")
            context.packageManager.getPackageInfo(context.packageName, 0)
        }

        val apkInstallTime = packageInfo.lastUpdateTime
        val versionMarker = File(outDir, ".apk_timestamp")
        val isNewApk = !versionMarker.exists() || versionMarker.readText().toLongOrNull() != apkInstallTime

        if (isNewApk) {
            Log.i("MainActivity", "New APK installation detected. Refreshing Python environment...")
            outDir.deleteRecursively()
            outDir.mkdirs()
            copyAssetFolder(context, "python", outDir)
            versionMarker.writeText(apkInstallTime.toString())
        } else if (BuildConfig.DEBUG) {
            // Fast development refresh: Overwrite main.py every time app launches
            Log.i("MainActivity", "Debug mode: Synchronizing main.py...")
            copySingleAsset(context, "python/main.py", File(outDir, "main.py"))
        }
    }

    private fun copySingleAsset(context: Context, assetPath: String, targetFile: File) {
        try {
            context.assets.open(assetPath).use { inStream ->
                FileOutputStream(targetFile).use { outStream -> inStream.copyTo(outStream) }
            }
        } catch (e: Exception) {
            Log.e("MainActivity", "Failed to update $assetPath: ${e.message}")
        }
    }

    private fun copyAssetFolder(context: Context, assetPath: String, outDir: File) {
        val am = context.assets
        val items = am.list(assetPath) ?: return
        if (!outDir.exists()) outDir.mkdirs()

        for (item in items) {
            val subPath = if (assetPath.isEmpty()) item else "$assetPath/$item"
            val subItems = am.list(subPath)

            if (!subItems.isNullOrEmpty()) {
                copyAssetFolder(context, subPath, File(outDir, item))
            } else {
                copySingleAsset(context, subPath, File(outDir, item))
            }
        }
    }
}