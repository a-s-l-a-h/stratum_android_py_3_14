## 🛠️ Quick Start

> **Note:** A complete pre-bundled workspace with all prebuilts included is available on the [v0.3 Release page](https://github.com/a-s-l-a-h/stratum_android_py_3_14/releases/tag/v0.3-tag).



### 1. Setup Python Prebuilts
Before building, you must download the official Android Python embeddable packages and place the prefix folders inside `python-prebuilts/`.

👉 Follow the step-by-step instructions in `python-prebuilts/README.md`.



# stratum_android_py_3_14

An embedded CPython 3.14 native Android application powered by the **Stratum**  bridge. It directly embeds the official Python C-API to run Python logic and benchmark raw JNI performance on Android.

<p align="center">
  <video src="https://github.com/user-attachments/assets/3384a2ff-e620-48a3-a091-89afdd81bce3" width="320" controls></video>
</p>

--- 

> **This demo project is based on [Stratum](https://github.com/a-s-l-a-h/stratum).**






---

## 🚀 Features

- **Embedded CPython 3.14**: Runs standalone native CPython without third-party packaging bloat.
- **Stratum Bridge**: Ultra-low overhead bidirectional calls between Python and Android Java/Kotlin SDKs.
- **16 KB Page Alignment**: Fully compatible with Android 15+ 16 KB memory page requirements.
- **Multi-ABI Support**: Pre-configured for both `arm64-v8a` (real hardware) and `x86_64` (Android emulator).
- **Fast Debug Hot-Sync**: In debug mode, user scripts (`main.py`) synchronize directly on app launch without needing to reinstall.

---

## 📂 Project Structure

```text
├── app/
│   ├── src/main/
│   │   ├── assets/python/          # Python user scripts (main.py)
│   │   ├── cpp/                    # Native C++ host (Python initialization & JNI)
│   │   └── java/com/example/stratum_android_py_3_14/ # Android UI & Lifecycle
├── python-prebuilts/               # Downloaded official Python 3.14 Android binaries
└── stratum-runtime/                # Stratum native runtime module
```

---

## 🛠️ Quick Start

### 1. Setup Python Prebuilts
Before building, you must download the official Android Python embeddable packages and place the `prefix` folders inside `python-prebuilts/`.

👉 **Follow the step-by-step instructions in [python-prebuilts/README.md](python-prebuilts/README.md).**

### 2. Open & Build in Android Studio
1. Open Android Studio (Ladybug or newer recommended).
2. Open this project root folder: `stratum_android_py_3_14`.
3. Let Gradle sync dependencies.
4. Select your target device (`arm64-v8a` device or `x86_64` emulator) and click **Run**.

---

## ⚙️ Package Details

- **Application ID / Namespace:** `com.example.stratum_android_py_3_14`
- **CPython Version:** `3.14`
- **Target SDK:** `36` (Android 15+)
- **Min SDK:** `24` (Android 7.0+)
