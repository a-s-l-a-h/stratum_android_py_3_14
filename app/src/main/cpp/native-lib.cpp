#include <jni.h>
#include <string>
#include <android/log.h>
#include <Python.h>

#define LOG_TAG "PythonHost"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

static bool g_initialized = false;

extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_stratum_1android_1py_13_114_PythonHost_initPython(
        JNIEnv *env, jclass, jstring python_home_path) {

    if (g_initialized || Py_IsInitialized()) return JNI_TRUE;

    const char *nativePath = env->GetStringUTFChars(python_home_path, nullptr);

    PyConfig config;
    PyConfig_InitIsolatedConfig(&config);

    config.install_signal_handlers = 0;
    config.use_environment = 0;
    config.user_site_directory = 0;
    config.site_import = 1;

    PyStatus status = PyConfig_SetBytesString(&config, &config.home, nativePath);
    if (PyStatus_Exception(status)) {
        LOGE("Failed to set Python Home: %s", nativePath);
        PyConfig_Clear(&config);
        env->ReleaseStringUTFChars(python_home_path, nativePath);
        return JNI_FALSE;
    }

    config.module_search_paths_set = 1;

#if defined(__aarch64__)
    const char *currentAbi = "arm64-v8a";
#elif defined(__x86_64__)
    const char *currentAbi = "x86_64";
#elif defined(__arm__)
    const char *currentAbi = "armeabi-v7a";
#elif defined(__i386__)
    const char *currentAbi = "x86";
#else
    const char *currentAbi = "unknown";
#endif

    std::string rootPath = std::string(nativePath);
    std::string stdlibPath = rootPath + "/stdlib";
    std::string dynloadAbiPath = rootPath + "/lib-dynload/" + currentAbi;
    std::string dynloadLegacyPath = rootPath + "/stdlib/lib-dynload";

    PyWideStringList_Append(&config.module_search_paths, Py_DecodeLocale(rootPath.c_str(), nullptr));
    PyWideStringList_Append(&config.module_search_paths, Py_DecodeLocale(stdlibPath.c_str(), nullptr));
    PyWideStringList_Append(&config.module_search_paths, Py_DecodeLocale(dynloadAbiPath.c_str(), nullptr));
    PyWideStringList_Append(&config.module_search_paths, Py_DecodeLocale(dynloadLegacyPath.c_str(), nullptr));

    status = Py_InitializeFromConfig(&config);
    PyConfig_Clear(&config);
    env->ReleaseStringUTFChars(python_home_path, nativePath);

    if (PyStatus_Exception(status)) {
        LOGE("Py_InitializeFromConfig failed");
        return JNI_FALSE;
    }

    PyObject *main_mod = PyImport_AddModule("__main__");
    PyObject *builtins = PyEval_GetBuiltins();
    if (main_mod && builtins) {
        PyObject *main_dict = PyModule_GetDict(main_mod);
        if (main_dict) {
            PyDict_SetItemString(main_dict, "__builtins__", builtins);
        }
    }

    PyErr_Clear();
    g_initialized = true;
    LOGI("Embedded Python 3.14 initialized successfully.");
    return JNI_TRUE;
}

extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_stratum_1android_1py_13_114_PythonHost_importModule(
        JNIEnv *env, jclass, jstring module_name) {

    if (!g_initialized && !Py_IsInitialized()) return JNI_FALSE;

    const char *name = env->GetStringUTFChars(module_name, nullptr);
    PyGILState_STATE gstate = PyGILState_Ensure();

    PyObject *pModule = PyImport_ImportModule(name);
    bool ok = (pModule != nullptr);
    if (!ok) PyErr_Print();
    Py_XDECREF(pModule);

    PyGILState_Release(gstate);
    env->ReleaseStringUTFChars(module_name, name);
    return ok ? JNI_TRUE : JNI_FALSE;
}

extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_stratum_1android_1py_13_114_PythonHost_onBackPressed(JNIEnv *, jclass) {
    if (!g_initialized && !Py_IsInitialized()) return JNI_FALSE;

    PyGILState_STATE gstate = PyGILState_Ensure();
    bool handled = false;

    PyObject *pModule = PyImport_ImportModule("main");
    if (pModule) {
        if (PyObject_HasAttrString(pModule, "onBackPressed")) {
            PyObject *pFunc = PyObject_GetAttrString(pModule, "onBackPressed");
            if (pFunc && PyCallable_Check(pFunc)) {
                PyObject *res = PyObject_CallObject(pFunc, nullptr);
                if (res) {
                    handled = (PyObject_IsTrue(res) == 1);
                    Py_DECREF(res);
                } else {
                    PyErr_Print();
                }
            }
            Py_XDECREF(pFunc);
        }
    } else {
        PyErr_Print();
    }
    Py_XDECREF(pModule);
    PyGILState_Release(gstate);
    return handled ? JNI_TRUE : JNI_FALSE;
}