
# Python Prebuilts Setup Guide

This directory holds the official CPython embeddable builds for Android. The Gradle build script reads headers and libraries from here to bundle Python into the APK.

---

## 📥 1. Download Official Python Binaries

Official Android releases page:  
👉 **[Python Downloads for Android](https://www.python.org/downloads/android/)**

Download the **Python 3.14.7** embeddable packages using the direct links below:

| Architecture | Android ABI | Direct Download Link |
|---|---|---|
| **aarch64** | `arm64-v8a` | [python-3.14.7-aarch64-linux-android.tar.gz](https://www.python.org/ftp/python/3.14.7/python-3.14.7-aarch64-linux-android.tar.gz) |
| **x86_64** | `x86_64` | [python-3.14.7-x86_64-linux-android.tar.gz](https://www.python.org/ftp/python/3.14.7/python-3.14.7-x86_64-linux-android.tar.gz) |

---

## 📦 2. How to Extract with 7-Zip

Windows does not extract `.tar.gz` files in a single step with the default file explorer. Use **7-Zip**:

1. **First Extraction:**  
   Right-click `python-3.14.7-*-linux-android.tar.gz` -> **7-Zip** -> **Extract Here**.  
   *(This gives you a `.tar` archive).*

2. **Second Extraction:**  
   Right-click the extracted `.tar` file -> **7-Zip** -> **Extract to "python-3.14.7-..."**.

3. **Locate the `prefix` folder:**  
   Inside the extracted folder, you will find a folder named **`prefix`**.

---

## 📁 3. Target Directory Layout

Copy and paste the extracted **`prefix`** folders so your `python-prebuilts` directory matches this structure exactly:

```text
python-prebuilts/
├── arm64-v8a/
│   └── prefix/
│       ├── include/
│       │   └── python3.14/
│       │       └── Python.h
│       └── lib/
│           ├── libpython3.14.so
│           └── python3.14/
│               ├── os.py
│               ├── sys.py
│               └── ...
└── x86_64/
    └── prefix/
        ├── include/
        │   └── python3.14/
        │       └── Python.h
        └── lib/
            ├── libpython3.14.so
            └── python3.14/
                ├── os.py
                ├── sys.py
                └── ...
```

---

## 🤖 Automated Build Integration

Once the `prefix` folders are placed above, `app/build.gradle.kts` automatically handles:
- Stripping test directories and unnecessary files to reduce APK size.
- Copying `python3.14/stdlib` into assets.
- Packing ABI-specific `lib-dynload` (`.so` extension modules) for each architecture.
- Bundling `libpython3.14.so` directly into `lib/<abi>/` in the final APK.