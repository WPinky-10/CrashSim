import tkinter as tk
from tkinter import ttk
import math
import numpy as np
import matplotlib.pyplot as plt
import os
import json
import datetime
from tkinter import filedialog
from openpyxl import Workbook

G = 9.81

# ---------------- SCROLLBAR STRUCTURE ----------------
class ScrollableFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)

        self.scrollable_frame = tk.Frame(self.canvas)

        self.window = self.canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw"
        )

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.scrollable_frame.bind("<Configure>", self._resize_scrollregion)
        self.canvas.bind("<Configure>", self._fit_width)

    def _resize_scrollregion(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _fit_width(self, event):
        self.canvas.itemconfig(self.window, width=event.width)
# ---------------- EXPORT STRUCTURE ----------------

BASE = "exports"
FOLDERS = ["graphs", "simulations", "telemetry", "csv", "excel"]

os.makedirs(BASE, exist_ok=True)
for f in FOLDERS:
    os.makedirs(os.path.join(BASE, f), exist_ok=True)


# ---------------- PHYSICS ----------------

def kmh_to_ms(v):
    return v / 3.6


def crash_profile(crash_type):
    if crash_type == "head-on":
        return 1.4, 0.8, 1.2
    if crash_type == "side":
        return 1.0, 1.1, 0.7
    if crash_type == "spin":
        return 0.6, 2.0, 0.4
    return 1.0, 1.0, 1.0


def get_k():
    mode = stiffness_var.get()

    if mode == "soft":
        return 140
    if mode == "hard":
        return 260
    if mode == "bumper":
        return 350
    if mode == "concrete":
        return 600
    if mode == "foam":
        return 90
    return float(k_entry.get())


def friction_factor():
    mode = friction_var.get()

    if mode == "dry":
        return 1.0
    if mode == "medium":
        return 0.85
    if mode == "wet":
        return 0.6
    return float(friction_entry.get())


def get_mass():
    mode = mass_var.get()

    if mode == "kart":
        return 150
    if mode == "bike":
        return 250
    if mode == "car":
        return 1200
    if mode == "truck":
        return 3500
    return float(mass_entry.get())


def g_force(v, k, friction, crash_type):
    peak, duration_factor, _ = crash_profile(crash_type)

    crush = math.sqrt((v ** 2) / (k * friction))
    accel = v ** 2 / (2 * crush)

    g = (accel / G) * peak
    duration = (2 * crush / v) * duration_factor

    return g, crush, duration


def severity(g):
    if g < 2: return "Negligible"
    if g < 3: return "Minimal"
    if g < 5: return "Very low"
    if g < 10: return "Low"
    if g < 25: return "Moderate"
    if g < 50: return "High"
    if g < 60: return "Very High"
    if g < 70: return "Severe"
    return "Extreme"


# ---------------- CALCULATION ----------------

def calculate():
    global last_results

    if speed_entry.get().strip() == "":
        return

    speed = float(speed_entry.get())
    v = kmh_to_ms(speed)

    k = get_k()
    f = friction_factor()
    crash = crash_var.get()
    mass = get_mass()

    g, crush, duration = g_force(v, k, f, crash)
    sev = severity(g)

    last_results = {
        "speed": speed,
        "v": v,
        "g": g,
        "crush": crush,
        "duration": duration,
        "mass": mass,
        "severity": sev
    }

    if save_history_var.get():
       history.append(last_results)

    g_label.set(f"{g:.2f} G")
    severity_label.set(sev)
    crush_label.set(f"{crush:.2f} m")
    duration_label.set(f"{duration:.3f} s")


# ---------------- GRAPHING ----------------

def build_pulse(v, g, duration):
    t = np.linspace(0, duration, 300)
    x = t / duration

    pulse = (x**1.6) * np.exp(-5.5 * x)
    pulse = pulse / np.max(pulse) * g

    return t, pulse


def plot_g():
    if last_results is None:
        return

    t, p = build_pulse(last_results["v"], last_results["g"], last_results["duration"])

    plt.figure()
    plt.plot(t, p)
    plt.title("G-force")
    plt.grid()
    plt.show()


def build_crash_signal(v, g_peak, duration):
    t = np.linspace(0, duration, 300)
    x = t / duration

    pulse = (x ** 1.6) * np.exp(-5.5 * x)
    pulse = pulse / np.max(pulse) * g_peak

    return t, pulse


def plot_velocity():
    if last_results is None:
        return

    v0 = last_results["v"]
    g = last_results["g"]
    duration = last_results["duration"]

    t, g_profile = build_crash_signal(v0, g, duration)
    a = g_profile * G

    dt = t[1] - t[0]
    v = v0 - np.cumsum(a) * dt
    v = np.clip(v, 0, None)

    plt.figure()
    plt.plot(t, v)
    plt.title("Velocity vs Time")
    plt.xlabel("Time (s)")
    plt.ylabel("m/s")
    plt.grid(True, alpha=0.3)
    plt.show()

# ---------------- SAVE / LOAD SIMULATION ----------------

def save_simulation():
    if last_results is None:
        return

    path = filedialog.asksaveasfilename(
        initialdir=os.path.join(BASE, "simulations"),
        defaultextension=".json"
    )

    if not path:
        return

    data = {
        "inputs": {
            "speed": speed_entry.get(),
            "mass_var": mass_var.get(),
            "mass_custom": mass_entry.get(),

            "stiffness_var": stiffness_var.get(),
            "k_custom": k_entry.get(),

            "friction_var": friction_var.get(),
            "friction_custom": friction_entry.get(),

            "crash_var": crash_var.get(),
        },
        "results": last_results
    }

    with open(path, "w") as f:
        json.dump(data, f, indent=4)


def load_simulation():
    global last_results

    path = filedialog.askopenfilename(
        initialdir=os.path.join(BASE, "simulations")
    )

    if not path:
        return

    with open(path, "r") as f:
        data = json.load(f)

    inputs = data.get("inputs", {})
    results = data.get("results", {})

    # ---- restore UI ----
    speed_entry.delete(0, tk.END)
    speed_entry.insert(0, inputs.get("speed", ""))

    mass_var.set(inputs.get("mass_var", "kart"))
    mass_entry.delete(0, tk.END)
    mass_entry.insert(0, inputs.get("mass_custom", ""))

    stiffness_var.set(inputs.get("stiffness_var", "soft"))
    k_entry.delete(0, tk.END)
    k_entry.insert(0, inputs.get("k_custom", ""))

    friction_var.set(inputs.get("friction_var", "dry"))
    friction_entry.delete(0, tk.END)
    friction_entry.insert(0, inputs.get("friction_custom", ""))

    crash_var.set(inputs.get("crash_var", "head-on"))

    show_mass_entry()
    show_k_entry()
    show_f_entry()

    last_results = results

def export_csv():
    path = filedialog.asksaveasfilename(
        initialdir=os.path.join(BASE, "csv"),
        defaultextension=".csv"
    )

    if not path:
        return

    sep = csv_sep_var.get()

    with open(path, "w", newline="") as f:
        f.write(f"Speed (km/h){sep}Mass (kg){sep}G-force{sep}Crush Distance (m){sep}Duration (sec){sep}Severity\n")

        for h in history:
            f.write(
                f'"{h["speed"]}"{sep}'
                f'"{h["mass"]}"{sep}'
                f'"{h["g"]}"{sep}'
                f'"{h["crush"]}"{sep}'
                f'"{h["duration"]}"{sep}'
                f'"{h["severity"]}"\n'
                    )
# export excel
def export_xlsx():
    if not history:
        return

    path = filedialog.asksaveasfilename(
        initialdir=os.path.join(BASE, "excel"),
        defaultextension=".xlsx",
        filetypes=[("Excel file", "*.xlsx")]
    )

    if not path:
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "CrashSim Data"

    # Header
    ws.append([
        "Speed (km/h)",
        "Mass (kg)",
        "G-force",
        "Crush Distance (m)",
        "Duration (sec)",
        "Severity"
    ])

    # Data
    for h in history:
        ws.append([
            h["speed"],
            h["mass"],
            h["g"],
            h["crush"],
            h["duration"],
            h["severity"]
        ])

    wb.save(path)


# ---------------- GENERAL UI ----------------

root = tk.Tk()
root.title("CrashSim v1.7.0")
root.geometry("300x460")

base_dir = os.path.dirname(__file__)
icon = tk.PhotoImage(file=os.path.join(base_dir, "IMG", "icon.png"))
root.iconphoto(True, icon)

nb = ttk.Notebook(root)
nb.pack(fill="both", expand=True)

vehicle_tab = tk.Frame(nb)
crash_tab = tk.Frame(nb)
telemetry_tab = tk.Frame(nb)
graph_tab = tk.Frame(nb)
data_tab = tk.Frame(nb)
info_tab = ScrollableFrame(nb)
info_tab.pack(fill="both", expand=True)

nb.add(vehicle_tab, text="Vehicle")
nb.add(crash_tab, text="Crash Setup")
nb.add(telemetry_tab, text="Telemetry")
nb.add(graph_tab, text="Graphs")
nb.add(data_tab, text="Data")
nb.add(info_tab, text="Info", sticky="nsew")



# ################## TABS #################

# ---------------- VEHICLE ----------------

tk.Label(vehicle_tab, text="VEHICLE", font=("Arial", 12, "bold")).pack(anchor="w")
tk.Label(vehicle_tab, text="Speed", font=("Arial", 9, "bold")).pack(anchor="w")
speed_entry = tk.Entry(vehicle_tab)
speed_entry.pack(anchor="w")

mass_var = tk.StringVar(value="kart")

tk.Label(vehicle_tab, text="Mass presets", font=("Arial", 9, "bold")).pack(anchor="w")

mass_frame = tk.Frame(vehicle_tab)
mass_frame.pack(anchor="w")

for t in [
    ("Kart (150kg)", "kart"),
    ("Motorbike (250kg)", "bike"),
    ("Car (1200kg)", "car"),
    ("Truck (3500kg)", "truck"),
    ("Custom weight", "custom")
]:
    tk.Radiobutton(mass_frame, text=t[0], variable=mass_var, value=t[1]).pack(anchor="w")

mass_entry = tk.Entry(mass_frame)

def show_mass_entry(*_):
    if mass_var.get() == "custom":
        mass_entry.pack(anchor="w")
    else:
        mass_entry.pack_forget()

mass_var.trace_add("write", show_mass_entry)




# ---------------- CRASH ----------------

tk.Label(crash_tab, text="CRASH SETUP", font=("Arial", 12, "bold")).pack(anchor="w")

stiffness_var = tk.StringVar(value="soft")
friction_var = tk.StringVar(value="dry")
crash_var = tk.StringVar(value="Head-on")

k_frame = tk.Frame(crash_tab)
k_frame.pack(anchor="w")

tk.Label(k_frame, text="Stiffness presets", font=("Arial", 9, "bold")).pack(anchor="w")

for t in [
    ("Soft Tire Barrier (140)", "soft"),
    ("Hard Tire Barrier (260)", "hard"),
    ("Bumper (350)", "bumper"),
    ("Concrete (600)", "concrete"),
    ("Foam (90)", "foam"),
    ("Custom K", "custom")
]:
    tk.Radiobutton(k_frame, text=t[0], variable=stiffness_var, value=t[1]).pack(anchor="w")

k_entry = tk.Entry(k_frame)

def show_k_entry(*_):
    if stiffness_var.get() == "custom":
        k_entry.pack(anchor="w")
    else:
        k_entry.pack_forget()

stiffness_var.trace_add("write", show_k_entry)

f_frame = tk.Frame(crash_tab)
f_frame.pack(anchor="w")

tk.Label(f_frame, text="Friction presets", font=("Arial", 9, "bold")).pack(anchor="w")

for t in [
    ("Dry (1.0)", "dry"),
    ("Intermediate (0.85)", "medium"),
    ("Wet (0.6)", "wet"),
    ("Custom μ", "custom")
]:
    tk.Radiobutton(f_frame, text=t[0], variable=friction_var, value=t[1]).pack(anchor="w")

friction_entry = tk.Entry(f_frame)

def show_f_entry(*_):
    if friction_var.get() == "custom":
        friction_entry.pack(anchor="w")
    else:
        friction_entry.pack_forget()

friction_var.trace_add("write", show_f_entry)

tk.Label(crash_tab, text="Crash Type", font=("Arial", 9, "bold")).pack(anchor="w")

for t in ["Head-on", "Side", "Spin"]:
    tk.Radiobutton(crash_tab, text=t, variable=crash_var, value=t).pack(anchor="w")


# ---------------- TELEMETRY ----------------

tk.Label(telemetry_tab, text="TELEMETRY", font=("Arial", 12, "bold")).pack(anchor="center")
save_history_var = tk.BooleanVar(value=False)

g_label = tk.StringVar()
severity_label = tk.StringVar()
crush_label = tk.StringVar()
duration_label = tk.StringVar()

tk.Label(telemetry_tab, textvariable=g_label).pack(anchor="center")
tk.Label(telemetry_tab, textvariable=severity_label).pack(anchor="center")
tk.Label(telemetry_tab, textvariable=crush_label).pack(anchor="center")
tk.Label(telemetry_tab, textvariable=duration_label).pack(anchor="center")

telemetry_text = tk.StringVar()


def advanced_telemetry():
    if last_results is None:
        return

    v = last_results["v"]
    g = last_results["g"]
    t = last_results["duration"]
    m = last_results["mass"]

    energy = 0.5 * m * v**2
    avg_g = (v / t) / G
    delta = g / t

    telemetry_text.set(f"""CRASH SIMULATION TELEMETRY REPORT
=================================

Severity Level: {last_results['severity']}

Peak G-Force: {g:.2f} G
Delta G Peak Rate: {delta:.2f} G/s
Impact Duration: {t:.3f} s
Crush Distance: {last_results['crush']:.2f} m
Impact Energy: {energy:.0f} J
Average Deceleration: {avg_g:.2f} G
""")


def export_telemetry():
    path = filedialog.asksaveasfilename(
        initialdir=os.path.join(BASE, "telemetry"),
        defaultextension=".txt"
    )

    if path:
        with open(path, "w") as f:
            f.write(telemetry_text.get())

tk.Checkbutton(
    telemetry_tab,
    text="Save in simulation history",
    variable=save_history_var
).pack(anchor="center")

tk.Button(telemetry_tab, text="Calculate", command=calculate).pack(anchor="center")
tk.Button(telemetry_tab, text="Advanced Telemetry", command=advanced_telemetry).pack(anchor="center")

tk.Label(telemetry_tab, textvariable=telemetry_text, justify="left").pack(anchor="center")


# ---------------- GRAPHS ----------------

tk.Label(graph_tab, text="GRAPHS", font=("Arial", 12, "bold")).pack(anchor="center")

tk.Button(graph_tab, text="G-force", command=plot_g).pack(anchor="center")
tk.Button(graph_tab, text="Velocity", command=plot_velocity).pack(anchor="center")


# ---------------- DATA ----------------
csv_sep_var = tk.StringVar(value=",")

tk.Label(data_tab, text="DATA", font=("Arial", 12, "bold")).pack(anchor="center")

tk.Button(data_tab, text="Export Telemetry", command=export_telemetry).pack(anchor="center")
tk.Button(data_tab, text="Save Simulation", command=save_simulation).pack(anchor="center")
tk.Button(data_tab, text="Load Simulation", command=load_simulation).pack(anchor="center")
tk.Button(data_tab, text="Export Excel (.xlsx)", command=export_xlsx).pack(anchor="center")
tk.Button(data_tab, text="Export CSV", command=export_csv).pack(anchor="center")
tk.Label(data_tab, text="CSV Separator", font=("Arial", 10, "bold")).pack(anchor="center")


sep_frame = tk.Frame(data_tab)
sep_frame.pack(anchor="center")

for text, val in [
    ("Comma (,)", ","),
    ("Semicolon (;)", ";"),
    ("Pipe (|)", "|")
]:
    tk.Radiobutton(sep_frame, text=text, variable=csv_sep_var, value=val).pack(anchor="w")





# ---------------- INFO ----------------

tk.Label(info_tab.scrollable_frame, text="INFO", font=("Arial", 12, "bold")).pack(anchor="w")

tk.Label(info_tab.scrollable_frame, text=
"""CrashSim v1.7.0
""", justify="left", wraplength=200).pack(anchor="w")

tk.Label(info_tab.scrollable_frame, text="Units & Scalars", font=("Arial", 9, "bold")).pack(anchor="w")
tk.Label(info_tab.scrollable_frame, text=
"""-kg: Weight (in kilograms)
-μ: Coefficient of Friction
-K: Stiffness of Barrier (in kN/m)
""", justify="left", wraplength=200).pack(anchor="w")

tk.Label(info_tab.scrollable_frame, text="Crash type definitions", font=("Arial", 9, "bold")).pack(anchor="w")
tk.Label(info_tab.scrollable_frame, text=
"""-Head-on: front impact with an object
-Side: lateral impact with an object
-Spin: loss of traction causing rotation
""", justify="left", wraplength=250).pack(anchor="w")

tk.Label(info_tab.scrollable_frame, text="G-force", font=("Arial", 9, "bold")).pack(anchor="w")
tk.Label(info_tab.scrollable_frame, text=
"""G-force is acceleration relative to gravity, where 1 g = 9.81 m/s². It describes the intensity of acceleration or deceleration during motion or impact and is used in CrashSim to estimate crash severity.

It is calculated as a / g, where a is acceleration in m/s² and g is 9.81 m/s². Positive values indicate acceleration forward, negative values indicate deceleration, which is most relevant in crashes. Peak G-force is more significant than average for injury prediction.
""", justify="left", wraplength=200).pack(anchor="w")

tk.Label(info_tab.scrollable_frame, text="Severity Scale", font=("Arial", 9, "bold")).pack(anchor="w")
tk.Label(info_tab.scrollable_frame, text=
"""-Negligible: not noticeable
-Minimal: barely noticeable
-Very low: slight movement
-Low: mild discomfort
-Moderate: temporary discomfort
-High: minor injury risk
-Very high: moderate injury risk
-Severe: serious injury or death risk
-Extreme: near-certain fatality
""", justify="left", wraplength=200).pack(anchor="w")

tk.Label(info_tab.scrollable_frame, text="Data Export Formats", font=("Arial", 9, "bold")).pack(anchor="w")
tk.Label(info_tab.scrollable_frame, text=
"""CSV, XLSX, TXT, JSON export supported
""", justify="left", wraplength=200).pack(anchor="w")

tk.Label(info_tab.scrollable_frame, text="Contributers", font=("Arial", 9, "bold")).pack(anchor="w")
tk.Label(info_tab.scrollable_frame, text=
"""Base code by William van den Hout
Design and icon by Hana Štrbová
""", justify="left", wraplength=200).pack(anchor="w")


tk.Label(info_tab.scrollable_frame, text="Dependencies", font=("Arial", 9, "bold")).pack(anchor="w")
tk.Label(info_tab.scrollable_frame, text=
"""-numpy: calculations
-matplotlib: graphs
-tkinter: UI
-openpyxl: Excel export

(Some may already be installed depending on system)
""", justify="left", wraplength=200).pack(anchor="w")

tk.Label(info_tab.scrollable_frame, text="Note", font=("Arial", 9, "bold")).pack(anchor="w")
tk.Label(info_tab.scrollable_frame, text=
"""This project is still in development and may contain bugs or unfinished features.
""", justify="left", wraplength=200).pack(anchor="w")
# ---------------- GLOBALS ----------------

last_results = None
history = []

root.mainloop()
#base code by William van den Hout
#icon by Hana Štrbová
