import gc
import importlib
import json
import math
import os
import platform
import re
import sys
import threading
import time
import datetime

import stratum
from stratum.ui import CustomCanvasView
from stratum.android.widget.LinearLayout import LinearLayout
from stratum.android.widget.FrameLayout import FrameLayout
from stratum.android.widget.TextView import TextView
from stratum.android.widget.Button import Button
from stratum.android.widget.EditText import EditText
from stratum.android.widget.ScrollView import ScrollView
from stratum.android.graphics.Paint import Paint
from stratum.android.graphics.Paint_Style import Paint_Style
from stratum.java.lang.Integer import Integer
from stratum.java.lang.String import String as JString
from stratum.java.util.Arrays import Arrays


def _opt(path, name):
    """Optional import: a class missing from your build must not kill the app."""
    try:
        return getattr(importlib.import_module(path), name)
    except Exception as e:
        stratum.log_msg("optional import failed %s.%s: %s" % (path, name, e))
        return None


HScroll = _opt("stratum.android.widget.HorizontalScrollView", "HorizontalScrollView")
SeekBar = _opt("stratum.android.widget.SeekBar", "SeekBar")
CheckBox = _opt("stratum.android.widget.CheckBox", "CheckBox")
Toast = _opt("stratum.android.widget.Toast", "Toast")
LP = _opt("stratum.android.widget.LinearLayout_LayoutParams", "LinearLayout_LayoutParams")
SensorManager = _opt("stratum.android.hardware.SensorManager", "SensorManager")
SensorEvent = _opt("stratum.android.hardware.SensorEvent", "SensorEvent")
ClipboardManager = _opt("stratum.android.content.ClipboardManager", "ClipboardManager")
ClipData = _opt("stratum.android.content.ClipData", "ClipData")
Build = _opt("stratum.android.os.Build", "Build")
Build_VERSION = _opt("stratum.android.os.Build_VERSION", "Build_VERSION")

# ─────────────────────────────────────────────────────────────────────────────
# Global state. GOLDEN RULE: every widget/manager is kept alive in KEEP,
# because a garbage-collected wrapper silently unregisters its listeners.
# ─────────────────────────────────────────────────────────────────────────────
KEEP = []
ACT = None
DENSITY = 2.75

DARK = dict(bg=0xFF101418, card=0xFF1B222B, text=0xFFEAF0F6, sub=0xFF8FA0B3)
LIGHT = dict(bg=0xFFF3F5F8, card=0xFFFFFFFF, text=0xFF1A2330, sub=0xFF5B6B7D)
ACCENT, ACCENT2, DANGER, NAVOFF = 0xFF00BFA5, 0xFF3D7BFF, 0xFFE5484D, 0xFF37474F
theme = dict(DARK)
themed = []

pages, nav_btns = {}, {}
current_page = "home"
title_tv = None
content_frame = None

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
TODO_PATH = os.path.join(DATA_DIR, "todos.json")
NOTES_PATH = os.path.join(DATA_DIR, "notes.txt")

TITLES = {
    "home": "Stratum Demo", "todo": "Tasks", "calc": "Calculator",
    "paint": "Sketchpad", "sensors": "Level & Motion", "timer": "Stopwatch",
    "notes": "Notes", "bench": "Bridge Benchmark", "settings": "Settings",
}
NAV = [("home", "Home"), ("todo", "Todo"), ("calc", "Calc"), ("paint", "Paint"),
       ("sensors", "Level"), ("timer", "Timer"), ("notes", "Notes"),
       ("bench", "Bench"), ("settings", "Settings")]


# ─────────────────────────────────────────────────────────────────────────────
# Small UI toolkit
# ─────────────────────────────────────────────────────────────────────────────
def keep(o):
    KEEP.append(o)
    return o


def set_text(view, text):
    """EditText only declares setText(CharSequence, BufferType), which hides
    TextView's 1-arg overload in the generated wrapper. Calling TextView's
    method directly on the same object avoids that."""
    TextView.setText(view, text)


def dp(x):
    return int(x * DENSITY)


def safe(fn):
    """An exception inside a callback would crash the app via a Java
    RuntimeException, so every UI callback goes through this."""
    def wrapper(*a):
        try:
            return fn(*a)
        except Exception as e:
            import traceback
            stratum.log_msg(traceback.format_exc())
            toast("Error: %s" % e)
    return wrapper


def toast(msg):
    try:
        if Toast:
            Toast.makeText(ACT, str(msg), 0).show()
    except Exception as e:
        stratum.log_msg("toast failed: %s" % e)


def _paint_role(v, role):
    if role in ("bg", "card"):
        v.setBackgroundColor(theme[role])
    elif role == "cardtext":
        v.setBackgroundColor(theme["card"])
        v.setTextColor(theme["text"])
    elif role == "input":
        v.setBackgroundColor(theme["card"])
        v.setTextColor(theme["text"])
        v.setHintTextColor(theme["sub"])
    else:
        v.setTextColor(theme[role])


def themed_view(v, role):
    themed.append((v, role))
    _paint_role(v, role)
    return v


def add(parent, child, w=-1, h=-2, weight=None, m=None):
    """addView with LinearLayout params. Falls back to a plain addView if
    LinearLayout_LayoutParams isn't in this build."""
    if LP is None:
        parent.addView(child)
        return child
    p = LP(w, h) if weight is None else LP(w, h, float(weight))
    if m:
        p.setMargins(dp(m[0]), dp(m[1]), dp(m[2]), dp(m[3]))
    parent.addView(child, p)
    return child


def vbox(role=None, pad=0):
    b = keep(LinearLayout(ACT))
    b.setOrientation(1)
    if pad:
        b.setPadding(dp(pad), dp(pad), dp(pad), dp(pad))
    if role:
        themed_view(b, role)
    return b


def hbox(role=None, pad=0):
    b = vbox(role, pad)
    b.setOrientation(0)
    return b


def label(text, size=14.0, role="text", gravity=None):
    tv = keep(TextView(ACT))
    tv.setText(text)
    tv.setTextSize(float(size))
    if gravity is not None:
        tv.setGravity(gravity)
    themed_view(tv, role)
    return tv


def button(text, fn, color=ACCENT, size=14.0):
    b = keep(Button(ACT))
    b.setText(text)
    b.setTextSize(float(size))
    b.setTextColor(0xFFFFFFFF)
    b.setBackgroundColor(color)
    try:
        b.setAllCaps(False)
    except Exception:
        pass
    b.setOnClickListener(safe(lambda v: fn()))
    return b


def card(parent, pad=12):
    c = vbox("card", pad)
    add(parent, c, m=(0, 0, 0, 10))
    return c


def edit(hint="", lines=1):
    et = keep(EditText(ACT))
    et.setHint(hint)
    if lines == 1:
        et.setSingleLine(True)
    else:
        et.setLines(lines)
        et.setGravity(48)  # Gravity.TOP
    et.setPadding(dp(10), dp(10), dp(10), dp(10))
    themed_view(et, "input")
    return et


def new_page(name, scroll=True):
    if scroll:
        sv = keep(ScrollView(ACT))
        sv.setFillViewport(True)
        content = vbox("bg", 14)
        sv.addView(content)
        themed_view(sv, "bg")
        view = sv
    else:
        content = vbox("bg", 10)
        view = content
    view.setVisibility(8)  # GONE
    content_frame.addView(view)
    pages[name] = view
    return content


def show_page(name):
    global current_page
    current_page = name
    for n, v in pages.items():
        v.setVisibility(0 if n == name else 8)  # VISIBLE / GONE
    for n, b in nav_btns.items():
        b.setBackgroundColor(ACCENT if n == name else NAVOFF)
    title_tv.setText(TITLES[name])
    if name == "home":
        refresh_home()
    elif name == "sensors":
        start_sensors()


# ─────────────────────────────────────────────────────────────────────────────
# Device info
# ─────────────────────────────────────────────────────────────────────────────
def get_specs():
    s = {"os": "Android", "api": "?", "hw": "?", "board": "?",
         "abi": platform.machine() or "arm64", "cores": str(os.cpu_count() or "?"),
         "py": sys.version.split()[0]}
    try:
        s["os"] = "Android %s" % Build_VERSION.sf_get_RELEASE()
        s["api"] = str(Build_VERSION.sf_get_SDK_INT())
        s["hw"] = str(Build.sf_get_HARDWARE())
        s["board"] = str(Build.sf_get_BOARD())
    except Exception:
        pass
    return s


SPECS = {}


def specs_text():
    s = SPECS
    return ("OS: %s (API %s)\nSoC: %s / %s\nCPU: %s cores (%s)\nPython: %s"
            % (s["os"], s["api"], s["hw"], s["board"], s["cores"], s["abi"], s["py"]))


# ─────────────────────────────────────────────────────────────────────────────
# 1. HOME
# ─────────────────────────────────────────────────────────────────────────────
home_date = home_stats = None


def build_home():
    global home_date, home_stats
    c = new_page("home")
    add(c, label("Stratum Demo", 26.0), m=(0, 4, 0, 0))
    add(c, label("A multi-screen Android app written 100% in Python.", 13.0, "sub"),
        m=(0, 0, 0, 10))
    home_date = label("", 15.0)
    add(c, home_date, m=(0, 0, 0, 6))
    home_stats = label("", 13.0, "sub")
    add(c, home_stats, m=(0, 0, 0, 12))

    info = card(c)
    add(info, label("This device", 13.0, "sub"))
    add(info, label(specs_text(), 14.0))

    add(c, label("Quick launch", 13.0, "sub"), m=(0, 4, 0, 6))
    grid = [("todo", "Tasks"), ("calc", "Calculator"), ("paint", "Sketchpad"),
            ("sensors", "Level"), ("timer", "Stopwatch"), ("notes", "Notes"),
            ("bench", "Benchmark"), ("settings", "Settings")]
    colors = [ACCENT, ACCENT2]
    for i in range(0, len(grid), 2):
        row = hbox()
        for j, (name, text) in enumerate(grid[i:i + 2]):
            add(row, button(text, lambda n=name: show_page(n), colors[(i // 2 + j) % 2], 15.0),
                w=0, h=dp(56), weight=1, m=(3, 3, 3, 3))
        add(c, row)


def refresh_home():
    now = datetime.datetime.now().strftime("%A, %d %B %Y   %H:%M")
    home_date.setText(now)
    open_n = sum(1 for t in todos if not t["d"])
    home_stats.setText("Open tasks: %d  |  Note chars: %d  |  Live callbacks: %d"
                       % (open_n, len(notes_text), stratum.callback_count()))


# ─────────────────────────────────────────────────────────────────────────────
# 2. TODO (persisted)
# ─────────────────────────────────────────────────────────────────────────────
todos = []
todo_list = todo_count = todo_input = None
row_views = []  # rows must stay referenced or their click listeners vanish


def load_todos():
    global todos
    try:
        with open(TODO_PATH, "r", encoding="utf-8") as f:
            todos = json.load(f)
    except Exception:
        todos = [{"t": "Try tapping this task", "d": False},
                 {"t": "Add your own above", "d": False}]


def save_todos():
    try:
        with open(TODO_PATH, "w", encoding="utf-8") as f:
            json.dump(todos, f)
    except Exception as e:
        stratum.log_msg("save_todos failed: %s" % e)


def render_todos():
    if todo_list is None:
        return
    todo_list.removeAllViews()
    row_views.clear()
    for i, t in enumerate(todos):
        tv = TextView(ACT)
        tv.setText(("[x]  " if t["d"] else "[  ]  ") + t["t"])
        tv.setTextSize(16.0)
        tv.setPadding(dp(12), dp(12), dp(12), dp(12))
        tv.setBackgroundColor(theme["card"])
        tv.setTextColor(theme["sub"] if t["d"] else theme["text"])
        tv.setOnClickListener(safe(lambda v, i=i: toggle_todo(i)))
        row_views.append(tv)
        add(todo_list, tv, m=(0, 3, 0, 3))
    todo_count.setText("%d open / %d total" % (sum(1 for t in todos if not t["d"]), len(todos)))


def toggle_todo(i):
    todos[i]["d"] = not todos[i]["d"]
    save_todos()
    render_todos()


def add_todo():
    text = str(todo_input.getText()).strip()
    if not text:
        toast("Type something first")
        return
    todos.append({"t": text, "d": False})
    set_text(todo_input, "")
    save_todos()
    render_todos()


def clear_done():
    global todos
    todos = [t for t in todos if not t["d"]]
    save_todos()
    render_todos()


def build_todo():
    global todo_list, todo_count, todo_input
    c = new_page("todo")
    todo_input = edit("New task...")
    add(c, todo_input)
    row = hbox()
    add(row, button("Add", add_todo), w=0, h=-2, weight=1, m=(0, 4, 4, 4))
    add(row, button("Clear done", clear_done, DANGER), w=0, h=-2, weight=1, m=(4, 4, 0, 4))
    add(c, row)
    todo_count = label("", 12.0, "sub")
    add(c, todo_count, m=(0, 6, 0, 6))
    todo_list = vbox()
    add(c, todo_list)
    render_todos()


# ─────────────────────────────────────────────────────────────────────────────
# 3. CALCULATOR
# ─────────────────────────────────────────────────────────────────────────────
calc_expr = ""
calc_disp = calc_hist_tv = None
calc_hist = []


def calc_eval(expr):
    if not expr or not re.fullmatch(r"[0-9+\-*/.() ]+", expr) or "**" in expr:
        raise ValueError("bad expression")
    expr = re.sub(r"(?<![\d.])0+(?=\d)", "", expr)  # "08" is a SyntaxError in py3
    val = eval(expr, {"__builtins__": {}}, {})
    if isinstance(val, float):
        if val == int(val) and abs(val) < 1e15:
            return str(int(val))
        return str(round(val, 10))
    return str(val)


def calc_press(k):
    global calc_expr
    if k == "C":
        calc_expr = ""
    elif k == "DEL":
        calc_expr = calc_expr[:-1]
    elif k == "=":
        try:
            res = calc_eval(calc_expr)
            calc_hist.append("%s = %s" % (calc_expr, res))
            del calc_hist[:-5]
            calc_hist_tv.setText("\n".join(calc_hist))
            calc_expr = res
        except Exception:
            calc_expr = ""
            calc_disp.setText("Error")
            return
    else:
        calc_expr += k
    calc_disp.setText(calc_expr or "0")


def build_calc():
    global calc_disp, calc_hist_tv
    c = new_page("calc", scroll=False)
    calc_hist_tv = label("", 12.0, "sub", gravity=5)  # right aligned
    add(c, calc_hist_tv, h=dp(80))
    calc_disp = label("0", 38.0, "text", gravity=5)
    add(c, calc_disp, m=(0, 0, 0, 8))
    rows = [["C", "(", ")", "DEL"], ["7", "8", "9", "/"], ["4", "5", "6", "*"],
            ["1", "2", "3", "-"], ["0", ".", "=", "+"]]
    for r in rows:
        row = hbox()
        for k in r:
            color = DANGER if k in ("C", "DEL") else ACCENT if k == "=" else \
                ACCENT2 if k in "/*-+()" else 0xFF455A64
            add(row, button(k, lambda k=k: calc_press(k), color, 20.0),
                w=0, h=-1, weight=1, m=(3, 3, 3, 3))
        add(c, row, h=0, weight=1)


# ─────────────────────────────────────────────────────────────────────────────
# 4. PAINT (CustomCanvasView)
# ─────────────────────────────────────────────────────────────────────────────
class DrawView(CustomCanvasView):
    def __init__(self, activity):
        super().__init__(activity)
        self.strokes = []
        self.color = 0xFFFFFFFF
        self.brush = 8.0
        self.line = Paint()
        self.line.setAntiAlias(True)
        self.line.setStyle(Paint_Style.sf_get_STROKE())
        self.dot = Paint()
        self.dot.setAntiAlias(True)
        self.dot.setStyle(Paint_Style.sf_get_FILL())

    def on_draw(self, canvas):
        canvas.drawColor(0xFF0B0F14)
        for s in self.strokes:
            if s["segs"]:
                self.line.setColor(s["c"])
                self.line.setStrokeWidth(s["w"])
                canvas.drawLines(s["segs"], self.line)   # one JNI call per stroke
            else:
                self.dot.setColor(s["c"])
                x, y = s["p"]
                canvas.drawCircle(x, y, s["w"] / 2.0, self.dot)

    def on_touch_event(self, event):
        a = event.getAction()
        x, y = float(event.getX()), float(event.getY())
        if a == 0:
            self.strokes.append({"c": self.color, "w": self.brush, "segs": [], "p": (x, y)})
        elif a == 2 and self.strokes:
            s = self.strokes[-1]
            px, py = s["p"]
            if abs(x - px) + abs(y - py) > 4:
                s["segs"].extend([px, py, x, y])
                s["p"] = (x, y)
        self.invalidate()
        return True


draw_view = None


def build_paint():
    global draw_view
    c = new_page("paint", scroll=False)
    draw_view = DrawView(ACT)
    keep(draw_view)
    add(c, draw_view, w=-1, h=0, weight=1)

    pal = hbox(pad=0)
    for col in (0xFFFFFFFF, 0xFFFF5252, 0xFFFFB300, 0xFF69F0AE, 0xFF40C4FF, 0xFFE040FB):
        b = button(" ", lambda col=col: setattr(draw_view, "color", col), col)
        add(pal, b, w=0, h=dp(44), weight=1, m=(3, 6, 3, 3))
    add(c, pal)

    def size(delta):
        draw_view.brush = max(2.0, min(48.0, draw_view.brush + delta))
        toast("Brush %d" % draw_view.brush)

    def undo():
        if draw_view.strokes:
            draw_view.strokes.pop()
            draw_view.invalidate()

    def clear():
        draw_view.strokes.clear()
        draw_view.invalidate()

    row = hbox()
    for text, fn, col in (("Undo", undo, ACCENT2), ("Clear", clear, DANGER),
                          ("Size -", lambda: size(-3.0), NAVOFF), ("Size +", lambda: size(3.0), NAVOFF)):
        add(row, button(text, fn, col, 13.0), w=0, weight=1, m=(3, 3, 3, 3))
    add(c, row)


# ─────────────────────────────────────────────────────────────────────────────
# 5. SENSORS (level bubble + shake counter)
# ─────────────────────────────────────────────────────────────────────────────
class BubbleView(CustomCanvasView):
    def __init__(self, activity):
        super().__init__(activity)
        self.ax = 0.0
        self.ay = 0.0
        self.ring = Paint()
        self.ring.setAntiAlias(True)
        self.ring.setStyle(Paint_Style.sf_get_STROKE())
        self.ring.setStrokeWidth(3.0)
        self.ring.setColor(0xFF2E7D6F)
        self.fill = Paint()
        self.fill.setAntiAlias(True)
        self.fill.setStyle(Paint_Style.sf_get_FILL())

    def set_tilt(self, ax, ay):
        self.ax += (ax - self.ax) * 0.25   # low-pass filter
        self.ay += (ay - self.ay) * 0.25
        self.invalidate()

    def on_draw(self, canvas):
        w, h = float(self.getWidth()), float(self.getHeight())
        cx, cy = w / 2.0, h / 2.0
        R = min(w, h) * 0.42
        canvas.drawColor(0xFF0B0F14)
        canvas.drawCircle(cx, cy, R, self.ring)
        canvas.drawCircle(cx, cy, R / 2.0, self.ring)
        canvas.drawLine(cx - R, cy, cx + R, cy, self.ring)
        canvas.drawLine(cx, cy - R, cx, cy + R, self.ring)
        k = R / 9.81
        bx, by = -self.ax * k, self.ay * k
        dist = math.hypot(bx, by)
        limit = R * 0.88
        if dist > limit:
            bx, by = bx * limit / dist, by * limit / dist
            dist = limit
        self.fill.setColor(0xFF69F0AE if dist < R * 0.08 else 0xFF00E5FF)
        canvas.drawCircle(cx + bx, cy + by, R * 0.12, self.fill)


bubble = sensor_mgr = sensor_acc = None
sensors_started = False
sens_tv = shake_tv = None
shakes, last_shake = 0, 0.0


def on_sensor(raw_event):
    global shakes, last_shake
    if current_page != "sensors":
        return
    ev = SensorEvent.from_ptr(raw_event)        # object params arrive as raw ints
    v = ev.f_get_values()
    x, y, z = v[0], v[1], v[2]
    bubble.set_tilt(x, y)
    sens_tv.setText("X %+6.2f   Y %+6.2f   Z %+6.2f  m/s2" % (x, y, z))
    mag = math.sqrt(x * x + y * y + z * z)
    now = time.time()
    if mag > 18.0 and now - last_shake > 0.5:
        shakes += 1
        last_shake = now
        shake_tv.setText("Shakes detected: %d" % shakes)


def start_sensors():
    global sensor_mgr, sensor_acc, sensors_started
    if sensors_started:
        return
    if SensorManager is None or SensorEvent is None:
        sens_tv.setText("SensorManager not in this build")
        return
    sensor_mgr = SensorManager.from_ptr(ACT.getSystemService("sensor"))
    keep(sensor_mgr)
    sensor_acc = sensor_mgr.getDefaultSensor(1)   # TYPE_ACCELEROMETER
    if not sensor_acc:
        sens_tv.setText("No accelerometer on this device")
        return
    keep(sensor_acc)
    sensor_mgr.registerListener({
        "onSensorChanged": safe(on_sensor),
        "onAccuracyChanged": lambda sensor, accuracy: None,
    }, sensor_acc, 2)                              # SENSOR_DELAY_UI
    sensors_started = True


def build_sensors():
    global bubble, sens_tv, shake_tv
    c = new_page("sensors", scroll=False)
    bubble = keep(BubbleView(ACT))
    add(c, bubble, w=-1, h=0, weight=1)
    sens_tv = label("Waiting for sensor...", 14.0, "text", gravity=17)
    add(c, sens_tv, m=(0, 8, 0, 0))
    shake_tv = label("Shakes detected: 0", 13.0, "sub", gravity=17)
    add(c, shake_tv)
    add(c, button("Reset shakes", lambda: reset_shakes(), NAVOFF), m=(0, 6, 0, 0))


def reset_shakes():
    global shakes
    shakes = 0
    shake_tv.setText("Shakes detected: 0")


# ─────────────────────────────────────────────────────────────────────────────
# 6. STOPWATCH (background thread -> UI thread)
# ─────────────────────────────────────────────────────────────────────────────
sw = {"running": False, "acc": 0.0, "t0": 0.0}
sw_label = laps_tv = None
laps = []


def fmt_time(sec):
    m, s = divmod(sec, 60)
    return "%02d:%05.2f" % (int(m), s)


def sw_elapsed():
    return sw["acc"] + (time.time() - sw["t0"] if sw["running"] else 0.0)


def _sw_update(txt):
    if sw["running"]:               # ignore stale posts after Stop
        sw_label.setText(txt)


def _sw_loop():
    while sw["running"]:
        stratum.run_on_ui_thread(_sw_update, fmt_time(sw_elapsed()))
        time.sleep(0.2)


def sw_start():
    if sw["running"]:
        return
    sw["t0"] = time.time()
    sw["running"] = True
    threading.Thread(target=_sw_loop, daemon=True).start()


def sw_stop():
    if not sw["running"]:
        return
    sw["acc"] = sw_elapsed()
    sw["running"] = False
    sw_label.setText(fmt_time(sw["acc"]))


def sw_lap():
    if sw["running"] or sw["acc"] > 0:
        laps.append("Lap %d   %s" % (len(laps) + 1, fmt_time(sw_elapsed())))
        laps_tv.setText("\n".join(reversed(laps[-12:])))


def sw_reset():
    sw["running"] = False
    sw["acc"] = 0.0
    laps.clear()
    sw_label.setText("00:00.00")
    laps_tv.setText("")


def build_timer():
    global sw_label, laps_tv
    c = new_page("timer")
    sw_label = label("00:00.00", 56.0, "text", gravity=17)
    add(c, sw_label, m=(0, 20, 0, 20))
    row = hbox()
    for text, fn, col in (("Start", sw_start, ACCENT), ("Stop", sw_stop, DANGER),
                          ("Lap", sw_lap, ACCENT2), ("Reset", sw_reset, NAVOFF)):
        add(row, button(text, fn, col), w=0, weight=1, m=(3, 3, 3, 3))
    add(c, row)
    laps_tv = label("", 15.0, "sub")
    add(c, laps_tv, m=(0, 14, 0, 0))


# ─────────────────────────────────────────────────────────────────────────────
# 7. NOTES (persisted)
# ─────────────────────────────────────────────────────────────────────────────
notes_text = ""
notes_et = notes_status = None


def load_notes():
    global notes_text
    try:
        with open(NOTES_PATH, "r", encoding="utf-8") as f:
            notes_text = f.read()
    except Exception:
        notes_text = ""


def save_notes():
    global notes_text
    notes_text = str(notes_et.getText())
    with open(NOTES_PATH, "w", encoding="utf-8") as f:
        f.write(notes_text)
    words = len(notes_text.split())
    notes_status.setText("Saved: %d chars, %d words  (%s)"
                         % (len(notes_text), words, datetime.datetime.now().strftime("%H:%M:%S")))


def build_notes():
    global notes_et, notes_status
    c = new_page("notes")
    notes_et = edit("Write something...", lines=12)
    set_text(notes_et, notes_text)
    add(c, notes_et)
    row = hbox()
    add(row, button("Save", save_notes), w=0, weight=1, m=(0, 6, 4, 6))
    add(row, button("Clear", lambda: set_text(notes_et, ""), DANGER), w=0, weight=1, m=(4, 6, 0, 6))
    add(c, row)
    notes_status = label("", 12.0, "sub")
    add(c, notes_status)


# ─────────────────────────────────────────────────────────────────────────────
# 8. BENCHMARK (runs on the UI thread, one test per post)
# ─────────────────────────────────────────────────────────────────────────────
bench_out = bench_btn = None
bench_lines = []
BENCH_BUDGET = 1.5   # max seconds per test, so the UI thread is never blocked long


def _loop(body, iters):
    """Run body() up to `iters` times or until BENCH_BUDGET seconds pass.
    Returns (count, elapsed_seconds)."""
    body()  # warm-up: resolves class/method slots
    n = 0
    t0 = time.perf_counter_ns()
    while n < iters:
        chunk = min(50, iters - n)
        for _ in range(chunk):
            body()
        n += chunk
        if (time.perf_counter_ns() - t0) / 1e9 > BENCH_BUDGET:
            break
    return n, (time.perf_counter_ns() - t0) / 1e9


def _result(n, el, detail):
    return n / el, (el / n) * 1e6, detail


def bt_static():
    n, el = _loop(lambda: Integer.compare(3, 30000), 60000)
    return _result(n, el, "%s calls" % format(n, ","))


def bt_instance():
    obj = Integer(12345)
    n, el = _loop(lambda: obj.intValue(), 60000)
    return _result(n, el, "%s calls" % format(n, ","))


def bt_string():
    n, el = _loop(lambda: JString("Stratum_Test_String_123").length(), 30000)
    return _result(n, el, "%s strings" % format(n, ","))


def bt_int_array():
    base = list(range(150, 0, -1))
    n, el = _loop(lambda: Arrays.sort(list(base)), 1500)
    return _result(n, el, "%s arrays (150 ints each)" % format(n, ","))


def bt_byte_array():
    payload = b"A" * (32 * 1024)

    def body():
        j = JString(payload, "ISO-8859-1")
        j.getBytes("ISO-8859-1")

    n, el = _loop(body, 1000)
    mbs = (n * 32 * 2) / 1024 / el
    return _result(n, el, "%.1f MB/s throughput" % mbs)


def bt_dict():
    data = {"user": "Android", "values": [10, 20, 30], "active": True, "score": 99.5}
    n, el = _loop(lambda: stratum.to_py(stratum.to_java(data)), 1000)
    return _result(n, el, "%s conversions" % format(n, ","))


def bt_gc():
    def body():
        Integer(7).intValue()

    n, el = _loop(body, 15000)
    return _result(n, el, "%s objects freed without crash" % format(n, ","))


BENCH_TESTS = [
    ("Static Method Dispatch", bt_static),
    ("Instance Method Call", bt_instance),
    ("String Marshalling", bt_string),
    ("int[] Array Marshalling", bt_int_array),
    ("byte[] Bridge Throughput", bt_byte_array),
    ("dict <-> HashMap Bridge", bt_dict),
    ("JNI GlobalRef / GC Churn", bt_gc),
]


def bench_refresh():
    bench_out.setText("\n".join(bench_lines))


def run_bench():
    bench_btn.setEnabled(False)
    bench_btn.setText("TESTING...")
    bench_lines.clear()
    bench_lines.append("Starting Benchmark Suite...")
    bench_lines.append("=" * 34)
    bench_refresh()
    idx = [0]
    total = len(BENCH_TESTS)

    def step():
        if idx[0] >= total:
            bench_lines.append("=" * 34)
            bench_lines.append("ALL BENCHMARKS FINISHED")
            bench_refresh()
            bench_btn.setEnabled(True)
            bench_btn.setText("RUN AGAIN")
            return
        name, fn = BENCH_TESTS[idx[0]]
        num = idx[0] + 1
        bench_lines.append("[%d/%d] %s: RUNNING..." % (num, total, name))
        bench_refresh()

        def run_single():
            gc.collect()
            try:
                ops, us, detail = fn()
                bench_lines[-1] = ("[%d/%d] %s: PASS\n   -> %s ops/sec (%.2f us/call) | %s"
                                   % (num, total, name, format(int(ops), ","), us, detail))
            except Exception as e:
                bench_lines[-1] = "[%d/%d] %s: FAILED (%s)" % (num, total, name, e)
            bench_refresh()
            idx[0] += 1
            bench_btn.post(safe(step))

        # yield first so "RUNNING..." is drawn before the test blocks the UI
        bench_btn.post(safe(run_single))

    bench_btn.post(safe(step))


def copy_bench():
    if not bench_lines:
        toast("Run the benchmark first")
        return
    if not (ClipboardManager and ClipData):
        toast("Clipboard classes not in build")
        return
    report = ("=== DEVICE HARDWARE SPECS ===\n" + specs_text()
              + "\n\n=== STRATUM BENCHMARK RESULTS ===\n" + "\n".join(bench_lines))
    cm = ClipboardManager.from_ptr(ACT.getSystemService("clipboard"))
    cm.setPrimaryClip(ClipData.newPlainText("Stratum Report", report))
    toast("Report copied")


def build_bench():
    global bench_out, bench_btn
    c = new_page("bench")
    add(c, label("Measures Python -> JNI -> Java round-trips.", 13.0, "sub"), m=(0, 0, 0, 8))
    row = hbox()
    bench_btn = button("START BENCHMARK", run_bench, ACCENT2)
    add(row, bench_btn, w=0, weight=1, m=(0, 4, 4, 4))
    add(row, button("COPY REPORT", copy_bench, NAVOFF), w=0, weight=1, m=(4, 4, 0, 4))
    add(c, row)
    bench_out = label("Press START BENCHMARK.\nResults appear here in real time.", 12.0)
    add(c, bench_out, m=(0, 12, 0, 0))


# ─────────────────────────────────────────────────────────────────────────────
# 9. SETTINGS
# ─────────────────────────────────────────────────────────────────────────────
size_preview = None


def apply_theme(dark):
    theme.clear()
    theme.update(DARK if dark else LIGHT)
    for v, role in themed:
        _paint_role(v, role)
    render_todos()


def copy_report():
    if not (ClipboardManager and ClipData):
        toast("Clipboard classes not in build")
        return
    cm = ClipboardManager.from_ptr(ACT.getSystemService("clipboard"))
    cm.setPrimaryClip(ClipData.newPlainText("Stratum", "Stratum Demo\n" + specs_text()))
    toast("Device info copied")


def reset_data():
    global todos, notes_text
    todos = []
    notes_text = ""
    for p in (TODO_PATH, NOTES_PATH):
        try:
            os.remove(p)
        except OSError:
            pass
    set_text(notes_et, "")
    render_todos()
    toast("All data cleared")


def on_size(progress):
    px = 10.0 + progress
    size_preview.setTextSize(px)
    notes_et.setTextSize(px)


def build_settings():
    global size_preview
    c = new_page("settings")

    a = card(c)
    add(a, label("Appearance", 13.0, "sub"))
    if CheckBox:
        cb = keep(CheckBox(ACT))
        cb.setText("Dark mode")
        cb.setTextSize(16.0)
        themed_view(cb, "text")
        cb.setChecked(True)
        cb.setOnCheckedChangeListener(safe(lambda btn, checked: apply_theme(bool(checked))))
        add(a, cb)

    b = card(c)
    add(b, label("Text size (also applies to Notes)", 13.0, "sub"))
    size_preview = label("The quick brown fox", 14.0)
    add(b, size_preview, m=(0, 4, 0, 4))
    if SeekBar:
        sb = keep(SeekBar(ACT))
        sb.setMax(20)
        sb.setProgress(4)
        sb.setOnSeekBarChangeListener({
            "onProgressChanged": safe(lambda s, p, user: on_size(p)),
            "onStartTrackingTouch": lambda s: None,
            "onStopTrackingTouch": lambda s: None,
        })
        add(b, sb)

    d = card(c)
    add(d, label("Tools", 13.0, "sub"))
    add(d, button("Show a Toast", lambda: toast("Hello from Python!"), ACCENT2), m=(0, 4, 0, 4))
    add(d, button("Copy device info", copy_report, ACCENT), m=(0, 4, 0, 4))
    add(d, button("Reset all data", reset_data, DANGER), m=(0, 4, 0, 4))

    e = card(c)
    add(e, label("About", 13.0, "sub"))
    add(e, label("Stratum Demo\nPure-Python UI over the Android SDK.\n" + specs_text(), 13.0))


# ─────────────────────────────────────────────────────────────────────────────
# Lifecycle entry points (auto-discovered by Stratum)
# ─────────────────────────────────────────────────────────────────────────────
def onCreate():
    global ACT, DENSITY, SPECS, title_tv, content_frame
    ACT = stratum.getActivity()
    keep(ACT)
    try:
        DENSITY = float(ACT.getResources().getDisplayMetrics().f_get_density())
    except Exception:
        pass
    SPECS = get_specs()
    load_todos()
    load_notes()

    root = vbox("bg")
    title_tv = TextView(ACT)
    keep(title_tv)
    title_tv.setTextSize(20.0)
    title_tv.setTextColor(0xFFFFFFFF)
    title_tv.setBackgroundColor(0xFF00796B)
    title_tv.setPadding(dp(16), dp(44), dp(16), dp(14))
    add(root, title_tv)

    content_frame = keep(FrameLayout(ACT))
    add(root, content_frame, w=-1, h=0, weight=1)

    build_home(); build_todo(); build_calc(); build_paint(); build_sensors()
    build_timer(); build_notes(); build_bench(); build_settings()

    nav = hbox("card", 4)
    for name, text in NAV:
        b = button(text, lambda n=name: show_page(n), NAVOFF, 12.0)
        nav_btns[name] = b
        add(nav, b, w=dp(84), h=-2, m=(2, 0, 2, 0))
    if HScroll:
        hs = keep(HScroll(ACT))
        hs.addView(nav)
        themed_view(hs, "card")
        add(root, hs)
    else:
        add(root, nav)

    stratum.setContentView(ACT, root)
    show_page("home")


def onBackPressed():
    if current_page != "home":
        show_page("home")
        return True
    return False


def onDestroy():
    sw["running"] = False