
# Native C++ Bridge Layer (`native-lib.cpp`)

This directory contains the native C++ code that initializes CPython inside the Android process and bridges lifecycle calls from Kotlin to Python.

---

## ⚠️ Critical JNI Naming Rule for Developers

When implementing this in your own app or changing the package name, **pay special attention to the exported JNI function names**.

In standard JNI (Oracle Java Native Interface specification):
1. **Dot (`.`)** in Java package names maps to a single underscore **`_`** in C.
2. **Literal Underscore (`_`)** inside a Java identifier **must be escaped as `_1` in C**.

### Current Implementation:
- **Kotlin Package:** `com.example.stratum_android_py_3_14`
- **Kotlin Class / Object:** `PythonHost`

Because the package contains multiple underscores (`stratum_android_py_3_14`), each underscore is escaped with `_1`:

```cpp
// 1. Python Engine Initialization
extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_stratum_1android_1py_13_114_PythonHost_initPython(
        JNIEnv *env, jclass, jstring python_home_path);

// 2. Python Module Import
extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_stratum_1android_1py_13_114_PythonHost_importModule(
        JNIEnv *env, jclass, jstring module_name);

// 3. Android Back-Button Handling
extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_stratum_1android_1py_13_114_PythonHost_onBackPressed(
        JNIEnv *env, jclass);
```

---

## 🔄 How to Adapt This to Your Own Codebase

If you change the Kotlin package name, update the C++ function declarations accordingly:

### Example A: Package WITHOUT underscores
- **Your Package:** `com.mycompany.myapp`
- **Your Object:** `PythonHost`
- **C++ JNI Signature:**
  ```cpp
  Java_com_mycompany_myapp_PythonHost_initPython(...)
  ```

### Example B: Package WITH underscores
- **Your Package:** `com.my_company.my_app`
- **Your Object:** `PythonHost`
- **C++ JNI Signature (`_` becomes `_1`):**
  ```cpp
  Java_com_my_1company_my_1app_PythonHost_initPython(...)
  ```

> **Warning:** If the C++ export name does not match the mangled package name, Android will throw `java.lang.UnsatisfiedLinkError: No implementation found for ...` at runtime.
