cmake_minimum_required(VERSION 3.22.1)
project("stratum_android_py_3_14")

# Set up prebuilt Python prefix paths for the current building ABI
set(PY_PREFIX "${PYTHON_PREBUILTS_ROOT}/${ANDROID_ABI}/prefix")
set(PY_INCLUDE "${PY_PREFIX}/include/python${PYTHON_VERSION}")
set(PY_LIB "${PY_PREFIX}/lib/libpython${PYTHON_VERSION}.so")

include_directories(
        ${PY_INCLUDE}
)

add_library(python3.14 SHARED IMPORTED)
set_target_properties(python3.14 PROPERTIES
        IMPORTED_LOCATION ${PY_LIB}
)

add_library(native-lib SHARED
        native-lib.cpp
)

# Enforce 16 KB page alignment for Android 15+ compatibility
target_link_options(native-lib PRIVATE
        "-Wl,-z,max-page-size=16384"
)

find_library(log-lib log)

target_link_libraries(native-lib
        python3.14
        ${log-lib}
)