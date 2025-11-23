# 🔥 Real GPU Benchmarking for Blender Rendering

This project lets you measure your actual GPU performance by rendering a real Blender scene and logging temperature, power, memory usage, and render time — all on your own PC.  
No simulations. Just real data, real charts, and real results.

---

## 📦 What This Does

- Runs Blender in the background to render a scene using your GPU.
- Logs GPU temperature, power usage, utilization, memory, and CPU usage every second.
- Saves a CSV file and a chart showing your GPU’s real performance.
- Helps you compare stock vs overclocked vs optimized cooling setups.

---

## 🧑‍💻 Who This Is For

- Non-technical users who want to test their GPU performance.
- Blender beginners or hobbyists.
- Gamers or creators curious about overclocking and cooling impact.
- Anyone with a GTX 660 or newer NVIDIA GPU.

---

## 🚀 Quick Start Guide (No Blender or Python Experience Needed)

### 1. Install Required Software
- [Blender](https://www.blender.org/download/) — install and note the path (e.g. `C:\Program Files\Blender Foundation\Blender 4.0\blender.exe`)
- [Python](https://www.python.org/downloads/) — check “Add Python to PATH” during install
- NVIDIA GPU driver — update from [nvidia.com](https://www.nvidia.com/Download/index.aspx)

### 2. Download a Blender Scene
- Example: [BMW27.blend](https://www.blender.org/download/demo-files/)
- Save it to a folder like `C:\bench\BMW27.blend`

### 3. Download This Repository
- Click **Code → Download ZIP**
- Unzip to a folder like `C:\bench\gpu-benchmark`

### 4. Install Python Packages
Open Command Prompt and run:
```bash
pip install pynvml psutil matplotlib pandas
