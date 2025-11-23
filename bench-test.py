import os
import sys
import time
import csv
import subprocess
import tempfile
import shutil
from datetime import datetime

import pynvml
import psutil
import pandas as pd
import matplotlib.pyplot as plt

# ====== USER CONFIG ======
BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe"  # change if needed
BLEND_FILE = r"C:\bench\BMW27.blend"  # path to your .blend scene
OUTPUT_DIR = r"C:\bench\results"      # where to save CSV/charts
OUTPUT_IMAGE = "benchmark_output.png" # final render output filename
RENDER_SAMPLES = 128                  # Cycles samples for the benchmark
RESOLUTION_X = 1920
RESOLUTION_Y = 1080

# ====== PREP ======
os.makedirs(OUTPUT_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_path = os.path.join(OUTPUT_DIR, f"gpu_benchmark_{timestamp}.csv")
chart_path = os.path.join(OUTPUT_DIR, f"gpu_benchmark_{timestamp}.png")
render_output_path = os.path.join(OUTPUT_DIR, OUTPUT_IMAGE)

# Validate Blender and scene
if not os.path.isfile(BLENDER_EXE):
    raise FileNotFoundError(f"Blender executable not found: {BLENDER_EXE}")
if not os.path.isfile(BLEND_FILE):
    raise FileNotFoundError(f"Blend file not found: {BLEND_FILE}")

# ====== BLENDER CONFIG SCRIPT (forces GPU, sets Cycles, resolution, samples) ======
blender_py = f"""
import bpy

# Set render engine to Cycles
bpy.context.scene.render.engine = 'CYCLES'

# Prefer GPU
prefs = bpy.context.preferences
cycles_prefs = prefs.addons['cycles'].preferences
cycles_prefs.compute_device_type = 'CUDA'  # or 'OPTIX' if supported

# Enable all CUDA devices
for d in cycles_prefs.get_devices():
    for dev in d:
        dev.use = True

# Device setting (GPU) at scene-level
bpy.context.scene.cycles.device = 'GPU'

# Set resolution and samples
bpy.context.scene.render.resolution_x = {RESOLUTION_X}
bpy.context.scene.render.resolution_y = {RESOLUTION_Y}
bpy.context.scene.cycles.samples = {RENDER_SAMPLES}

# Output settings
bpy.context.scene.render.filepath = r"{render_output_path}"
bpy.context.scene.render.image_settings.file_format = 'PNG'
"""

# Write temp script
tmp_dir = tempfile.mkdtemp(prefix="blender_bench_")
tmp_script = os.path.join(tmp_dir, "configure_cycles_gpu.py")
with open(tmp_script, "w", encoding="utf-8") as f:
    f.write(blender_py)

# ====== INIT NVML ======
pynvml.nvmlInit()
device_count = pynvml.nvmlDeviceGetCount()
if device_count == 0:
    raise RuntimeError("No NVIDIA GPUs detected.")

# Use GPU 0 by default
handle = pynvml.nvmlDeviceGetHandleByIndex(0)
gpu_name = pynvml.nvmlDeviceGetName(handle).decode()
print(f"Benchmarking GPU: {gpu_name}")

# ====== START BLENDER RENDER (BACKGROUND) ======
# We run Blender configured script first (to set GPU), then render
cmd = [
    BLENDER_EXE,
    "-b", BLEND_FILE,
    "-P", tmp_script,
    "-o", render_output_path,   # ensure output
    "-F", "PNG",
    "-f", "1"                   # render frame 1
]

start_time = time.time()
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

# ====== TELEMETRY POLLING LOOP ======
fields = ["t_sec","gpu_temp_c","gpu_power_w","gpu_util_pct","gpu_mem_used_mb","cpu_util_pct","proc_alive"]
with open(csv_path, "w", newline="", encoding="utf-8") as cf:
    writer = csv.writer(cf)
    writer.writerow(["gpu_name", gpu_name])
    writer.writerow(["blend_file", BLEND_FILE])
    writer.writerow(["samples", RENDER_SAMPLES])
    writer.writerow(["resolution", f"{RESOLUTION_X}x{RESOLUTION_Y}"])
    writer.writerow([])  # separator
    writer.writerow(fields)

    while True:
        poll_time = time.time() - start_time
        try:
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        except:
            temp = None

        try:
            pwr = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # mW -> W
        except:
            pwr = None

        try:
            util = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
        except:
            util = None

        try:
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle).used / (1024*1024)
        except:
            mem = None

        cpu_util = psutil.cpu_percent(interval=None)

        # Check if process is still alive
        proc_alive = proc.poll() is None

        writer.writerow([f"{poll_time:.2f}", temp, pwr, util, f"{mem:.0f}", f"{cpu_util:.0f}", int(proc_alive)])

        if not proc_alive:
            break

        time.sleep(1.0)

end_time = time.time()
elapsed = end_time - start_time
stdout, stderr = proc.communicate()

# Clean temp files
shutil.rmtree(tmp_dir, ignore_errors=True)

print(f"Render finished in {elapsed:.2f} seconds.")
if stderr:
    print("Blender stderr (if any):")
    print(stderr)

print(f"CSV saved to: {csv_path}")
print(f"Output image: {render_output_path}")

# ====== LOAD DATA AND CHART ======
df = pd.read_csv(csv_path, skiprows=5)  # skip header rows we wrote
if df.empty:
    print("No telemetry captured. Check Blender execution and paths.")
    sys.exit(0)

plt.figure(figsize=(12,8))

plt.subplot(2,2,1)
plt.plot(df["t_sec"], df["gpu_temp_c"], color="red")
plt.title("GPU temperature over time")
plt.xlabel("Time (s)")
plt.ylabel("Temperature (°C)")
plt.grid(alpha=0.3)

plt.subplot(2,2,2)
plt.plot(df["t_sec"], df["gpu_power_w"], color="green")
plt.title("GPU power over time")
plt.xlabel("Time (s)")
plt.ylabel("Power (W)")
plt.grid(alpha=0.3)

plt.subplot(2,2,3)
plt.plot(df["t_sec"], df["gpu_util_pct"], color="blue")
plt.title("GPU utilization over time")
plt.xlabel("Time (s)")
plt.ylabel("Utilization (%)")
plt.grid(alpha=0.3)

plt.subplot(2,2,4)
plt.plot(df["t_sec"], df["gpu_mem_used_mb"], color="purple")
plt.title("GPU memory usage over time")
plt.xlabel("Time (s)")
plt.ylabel("Memory used (MB)")
plt.grid(alpha=0.3)

plt.suptitle(f"Real render benchmark: {gpu_name} | {os.path.basename(BLEND_FILE)} | {RESOLUTION_X}x{RESOLUTION_Y} | {RENDER_SAMPLES} samples\nElapsed: {elapsed:.1f}s", fontsize=10)
plt.tight_layout(rect=[0,0,1,0.94])
plt.savefig(chart_path, dpi=150)
plt.show()

print(f"Chart saved to: {chart_path}")
