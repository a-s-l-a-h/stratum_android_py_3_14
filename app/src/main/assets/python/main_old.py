import gc
import os
import sys
import time
import platform
import stratum

# UI Widgets
from stratum.android.widget.LinearLayout import LinearLayout
from stratum.android.widget.TextView import TextView
from stratum.android.widget.Button import Button
from stratum.android.widget.ScrollView import ScrollView

# SDK Benchmark Target Classes
from stratum.java.lang.String import String as JString
from stratum.java.lang.Integer import Integer
from stratum.java.util.Arrays import Arrays

# Safe Import of Android System Info (Hardware only, no personal identifiers)
try:
    from stratum.android.os.Build import Build
    from stratum.android.os.Build_VERSION import Build_VERSION
except Exception:
    Build = None
    Build_VERSION = None

# Safe Import of Android Clipboard
try:
    from stratum.android.content.ClipboardManager import ClipboardManager
    from stratum.android.content.ClipData import ClipData
except Exception:
    ClipboardManager = None
    ClipData = None


# ---------------------------------------------------------------------------
# Device Spec Collector (Privacy-Safe: Hardware / OS specs only)
# ---------------------------------------------------------------------------

def get_hardware_specs():
    specs = {
        "os_release": "Android",
        "api_level": "Unknown",
        "hardware": "Unknown",
        "board": "Unknown",
        "abi": platform.machine() or "arm64",
        "cores": str(os.cpu_count() or "Unknown"),
        "py_ver": sys.version.split()[0],
    }

    if Build_VERSION:
        try:
            specs["os_release"] = f"Android {Build_VERSION.sf_get_RELEASE()}"
            specs["api_level"] = str(Build_VERSION.sf_get_SDK_INT())
        except Exception:
            pass

    if Build:
        try:
            specs["hardware"] = str(Build.sf_get_HARDWARE())
            specs["board"] = str(Build.sf_get_BOARD())
            abis = Build.sf_get_SUPPORTED_ABIS()
            if abis and len(abis) > 0:
                specs["abi"] = str(abis[0])
        except Exception:
            pass

    return specs


# ---------------------------------------------------------------------------
# Individual Bridge Benchmark Tests
# ---------------------------------------------------------------------------

def test_static_call():
    """Tests raw slot-table dispatch speed calling Java static methods."""
    iters = 60_000
    Integer.compare(1, 2)  # warm-up slot

    t0 = time.perf_counter_ns()
    for i in range(iters):
        Integer.compare(i, 30_000)
    elapsed = (time.perf_counter_ns() - t0) / 1e9

    ops = iters / elapsed
    us = (elapsed / iters) * 1e6
    return ops, us, f"{iters:,} calls"


def test_instance_call():
    """Tests calling an instance method on a live Java object reference."""
    iters = 60_000
    obj = Integer(12345)
    obj.intValue()  # warm-up

    t0 = time.perf_counter_ns()
    for _ in range(iters):
        obj.intValue()
    elapsed = (time.perf_counter_ns() - t0) / 1e9

    ops = iters / elapsed
    us = (elapsed / iters) * 1e6
    return ops, us, f"{iters:,} calls"


def test_string_bridge():
    """Tests Stratum C++ UTF-8 -> UTF-16 string conversion and object creation."""
    iters = 30_000
    sample = "Stratum_Test_String_123"

    t0 = time.perf_counter_ns()
    for _ in range(iters):
        j = JString(sample)
        _ = j.length()
    elapsed = (time.perf_counter_ns() - t0) / 1e9

    ops = iters / elapsed
    us = (elapsed / iters) * 1e6
    return ops, us, f"{iters:,} strings"


def test_int_array():
    """Tests marshalling Python list -> Java int[] and sorting."""
    iters = 1_500
    base = list(range(150, 0, -1))

    t0 = time.perf_counter_ns()
    for _ in range(iters):
        arr = list(base)
        Arrays.sort(arr)
    elapsed = (time.perf_counter_ns() - t0) / 1e9

    ops = iters / elapsed
    us = (elapsed / iters) * 1e6
    return ops, us, f"{iters:,} arrays (150 ints each)"


def test_byte_array():
    """Tests bidirectional byte[] transfer across native bridge."""
    iters = 1_000
    payload = b"A" * (32 * 1024)  # 32 KB payload

    t0 = time.perf_counter_ns()
    for _ in range(iters):
        j = JString(payload, "ISO-8859-1")
        _ = j.getBytes("ISO-8859-1")
    elapsed = (time.perf_counter_ns() - t0) / 1e9

    mb_transferred = (iters * 32 * 2) / 1024
    speed_mbs = mb_transferred / elapsed
    ops = iters / elapsed
    us = (elapsed / iters) * 1e6
    return ops, us, f"{speed_mbs:.1f} MB/s throughput"


def test_dict_conversion():
    """Tests bidirectional Python dict <-> Java HashMap conversion."""
    iters = 1_000
    data = {
        "user": "Android",
        "values": [10, 20, 30],
        "active": True,
        "score": 99.5
    }

    t0 = time.perf_counter_ns()
    for _ in range(iters):
        j_obj = stratum.to_java(data)
        _ = stratum.to_py(j_obj)
    elapsed = (time.perf_counter_ns() - t0) / 1e9

    ops = iters / elapsed
    us = (elapsed / iters) * 1e6
    return ops, us, f"{iters:,} conversions"


def test_gc_churn():
    """Tests creating and freeing 15,000 JNI references to verify JniLocalFrame."""
    iters = 15_000

    t0 = time.perf_counter_ns()
    for i in range(iters):
        obj = Integer(i)
        _ = obj.intValue()
    elapsed = (time.perf_counter_ns() - t0) / 1e9

    ops = iters / elapsed
    us = (elapsed / iters) * 1e6
    return ops, us, f"{iters:,} objects freed without crash"


# ---------------------------------------------------------------------------
# Android UI Activity Entry Point
# ---------------------------------------------------------------------------

def onCreate():
    activity = stratum.getActivity()
    specs = get_hardware_specs()

    root = LinearLayout(activity)
    root.setOrientation(1)
    root.setBackgroundColor(0xFF141414)
    root.setPadding(24, 32, 24, 24)

    # 1. Header Title
    tv_title = TextView(activity)
    tv_title.setText("STRATUM BRIDGE BENCHMARK")
    tv_title.setTextSize(18.0)
    tv_title.setTextColor(0xFF00E5FF)
    tv_title.setPadding(0, 0, 0, 12)
    root.addView(tv_title)

    # 2. Hardware Specs Card (Top)
    spec_summary = (
        f"• OS / API: {specs['os_release']} (API {specs['api_level']})\n"
        f"• SoC / Board: {specs['hardware']} ({specs['board']})\n"
        f"• CPU / Arch: {specs['cores']} Cores ({specs['abi']})\n"
        f"• Python: {specs['py_ver']} (64-bit)"
    )

    tv_specs = TextView(activity)
    tv_specs.setText(spec_summary)
    tv_specs.setTextSize(12.0)
    tv_specs.setTextColor(0xFFE0E0E0)
    tv_specs.setBackgroundColor(0xFF222222)
    tv_specs.setPadding(20, 16, 20, 16)
    root.addView(tv_specs)

    # 3. Action Buttons Container
    btn_container = LinearLayout(activity)
    btn_container.setOrientation(0)  # Horizontal layout
    btn_container.setPadding(0, 16, 0, 16)

    btn_run = Button(activity)
    btn_run.setText("START BENCHMARK")
    btn_run.setBackgroundColor(0xFF007ACC)
    btn_run.setTextColor(0xFFFFFFFF)

    btn_copy = Button(activity)
    btn_copy.setText("COPY REPORT")
    btn_copy.setBackgroundColor(0xFF424242)
    btn_copy.setTextColor(0xFFFFFFFF)

    btn_container.addView(btn_run)
    btn_container.addView(btn_copy)
    root.addView(btn_container)

    # 4. Output Console
    tv_console = TextView(activity)
    tv_console.setText("Press 'START BENCHMARK' to test the bridge.\nResults will appear here in real-time.")
    tv_console.setTextSize(11.5)
    tv_console.setTextColor(0xFF00FF66)
    tv_console.setBackgroundColor(0xFF0A0A0A)
    tv_console.setPadding(18, 18, 18, 18)

    scroll = ScrollView(activity)
    scroll.addView(tv_console)
    root.addView(scroll)

    # Benchmark State
    tests = [
        ("Static Method Dispatch", test_static_call),
        ("Instance Method Call", test_instance_call),
        ("String Marshalling", test_string_bridge),
        ("int[] Array Marshalling", test_int_array),
        ("byte[] Bridge Throughput", test_byte_array),
        ("dict <-> HashMap Bridge", test_dict_conversion),
        ("JNI GlobalRef / GC Churn", test_gc_churn),
    ]

    log_lines = []

    def refresh_screen():
        tv_console.setText("\n".join(log_lines))
        scroll.fullScroll(130)  # Scroll to bottom

    # --- Copy to Clipboard Handler ---
    def on_copy_click(_=None):
        if not log_lines:
            btn_copy.setText("RUN FIRST!")
            def reset_copy_txt():
                btn_copy.setText("COPY REPORT")
            root.post(reset_copy_txt)
            return

        # Prepare formatted text block
        report_text = (
            "=== DEVICE HARDWARE SPECS ===\n"
            + spec_summary + "\n\n"
            "=== STRATUM BENCHMARK RESULTS ===\n"
            + "\n".join(log_lines)
        )

        copied = False
        if ClipboardManager and ClipData:
            try:
                raw_cm = activity.getSystemService("clipboard")
                cm = ClipboardManager.from_ptr(raw_cm)
                clip = ClipData.newPlainText("Stratum Report", report_text)
                cm.setPrimaryClip(clip)
                copied = True
            except Exception as e:
                stratum.log_msg(f"Clipboard copy failed: {e}")

        if copied:
            btn_copy.setText("COPIED!")
        else:
            btn_copy.setText("COPY FAILED")

        def restore_btn():
            time.sleep(1.8)
            def do_restore():
                btn_copy.setText("COPY REPORT")
            root.post(do_restore)

        # Non-blocking reset
        import threading
        threading.Thread(target=restore_btn, daemon=True).start()

    btn_copy.setOnClickListener(on_copy_click)

    # --- Benchmark Execution Loop ---
    def start_suite(_=None):
        btn_run.setEnabled(False)
        btn_run.setText("TESTING...")
        log_lines.clear()
        log_lines.append("Starting Benchmark Suite...")
        log_lines.append("=" * 40)
        refresh_screen()

        step_idx = 0

        def execute_next_step():
            nonlocal step_idx
            if step_idx < len(tests):
                name, fn = tests[step_idx]
                step_num = step_idx + 1
                total = len(tests)

                # 1. Update text showing current test is active
                log_lines.append(f"[{step_num}/{total}] {name}: RUNNING...")
                refresh_screen()

                # 2. Yield to Android Choreographer so "RUNNING..." draws to screen before test executes
                def run_single():
                    gc.collect()
                    try:
                        ops, us, detail = fn()
                        log_lines[-1] = (
                            f"[{step_num}/{total}] {name}: PASS\n"
                            f"   -> {ops:,.0f} ops/sec ({us:.2f} µs/call) | {detail}"
                        )
                    except Exception as e:
                        log_lines[-1] = f"[{step_num}/{total}] {name}: FAILED ({e})"

                    refresh_screen()
                    nonlocal step_idx
                    step_idx += 1
                    root.post(execute_next_step)

                root.post(run_single)

            else:
                # Finished all tests
                log_lines.append("=" * 40)
                log_lines.append("ALL BENCHMARKS FINISHED")
                refresh_screen()
                btn_run.setEnabled(True)
                btn_run.setText("RUN AGAIN")

        root.post(execute_next_step)

    btn_run.setOnClickListener(start_suite)

    stratum.setContentView(activity, root)