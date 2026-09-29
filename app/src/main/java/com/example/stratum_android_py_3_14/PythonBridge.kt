package com.example.stratum_android_py_3_14

object PythonHost {
    init {
        System.loadLibrary("python3.14")
        System.loadLibrary("native-lib")
    }

    @JvmStatic external fun initPython(pythonHomePath: String): Boolean
    @JvmStatic external fun importModule(moduleName: String): Boolean
    @JvmStatic external fun onBackPressed(): Boolean
}