import json
import tkinter as tk
from PIL import Image, ImageTk
from tkinter import messagebox
import csv
import sys
import os

# ====== 路径修正 ======
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

BASE_DIR = SCRIPT_DIR
IMG_DIR = os.path.join(BASE_DIR, "images")
CACHE_FILE = os.path.join(BASE_DIR, "success_cache.json")
COLOR_CSV = os.path.join(BASE_DIR, "color_ratio_ranking.csv")
FAV_FILE = os.path.join(BASE_DIR, "favorites.json")

# ====== 读取数据 ======
try:
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        cache = json.load(f)
except Exception as e:
    print(f"❌ 错误: 无法加载缓存文件 {e}")
    sys.exit(1)

color_ranks = {}
if os.path.exists(COLOR_CSV):
    with open(COLOR_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tpl_id = str(row["TemplateID"])
            color_ranks[tpl_id] = {
                "GreenRank": int(row["GreenRank"]),
                "BlueRank": int(row["BlueRank"]),
                "GreenRatio": float(row["GreenRatio"]),
                "BlueRatio": float(row["BlueRatio"]),
            }

# 加载收藏夹
favorites = []
if os.path.exists(FAV_FILE):
    try:
        with open(FAV_FILE, "r", encoding="utf-8") as f:
            favorites = json.load(f)
    except: favorites = []

all_skins = list(cache.values())
image_index = {}
if os.path.exists(IMG_DIR):
    for root_dir, _, files in os.walk(IMG_DIR):
        for f in files:
            if f.endswith(".png"):
                parts = f.split("_")
                try:
                    seed = int(parts[0])
                    side = "playside" if "playside" in f else "backside"
                    image_index[(seed, side)] = os.path.join(root_dir, f)
                except: continue

# ====== GUI 状态 ======
current_index = 0
photo = None
image_visible = False
sort_mode = 1
search_window = None

# ====== Tk 主窗口 ======
root = tk.Tk()
root.title("Gamma Doppler Phase 3 Viewer")

# --- 图片显示区域 ---
img_label = tk.Label(root)

# ====== 信息展示区 ======
info_frame = tk.Frame(root)
info_frame.pack(pady=5, padx=20)

info_text = tk.Label(info_frame, font=("Arial", 10), justify="left", anchor="w")
info_text.pack(side=tk.LEFT)

bar_canvas = tk.Canvas(info_frame, width=220, height=60)
bar_canvas.pack(side=tk.LEFT, padx=10)

def draw_color_bar(g, b):
    bar_canvas.delete("all")
    max_w = 140
    bar_canvas.create_text(5, 15, text="G", anchor="w")
    bar_canvas.create_rectangle(25, 8, 25 + int(max_w*g), 22, fill="#00aa00", outline="")
    bar_canvas.create_text(175, 15, text=f"{g:.2%}", anchor="w", font=("Arial", 9))

    bar_canvas.create_text(5, 40, text="B", anchor="w")
    bar_canvas.create_rectangle(25, 33, 25 + int(max_w*b), 47, fill="#0066ff", outline="")
    bar_canvas.create_text(175, 40, text=f"{b:.2%}", anchor="w", font=("Arial", 9))

# ====== 核心控制 ======
def show_single():
    global photo
    skins = get_sorted_skins()
    if not skins: return

    d = skins[current_index]
    tpl_id = str(d["paint_seed"])
    cr = color_ranks.get(tpl_id, {})

    # 检查是否已收藏
    is_fav = tpl_id in [str(s) for s in favorites]
    fav_status = "⭐ 已收藏" if is_fav else ""

    if image_visible:
        key = (d["paint_seed"], "playside")
        if key in image_index:
            img = Image.open(image_index[key])
            img.thumbnail((700, 500))
            photo = ImageTk.PhotoImage(img)
            img_label.config(image=photo)
            img_label.pack(side=tk.TOP, before=info_frame)
        else:
            img_label.config(image="", text="Missing Image")
            img_label.pack(side=tk.TOP, before=info_frame)
    else:
        img_label.pack_forget()

    info_text.config(text=(
        f"{current_index+1}/{len(skins)} | ID: {tpl_id} {fav_status}\n"
        f"Float: {d['float']:.5f}\n"
        f"G-Rank: #{cr.get('GreenRank','-')} | B-Rank: #{cr.get('BlueRank','-')}"
    ))
    draw_color_bar(cr.get("GreenRatio", 0), cr.get("BlueRatio", 0))

def get_sorted_skins():
    skins = all_skins.copy()
    if sort_mode == 2:
        skins.sort(key=lambda x: (-color_ranks.get(str(x["paint_seed"]), {}).get("GreenRatio", 0), x["paint_seed"]))
    elif sort_mode == 3:
        skins.sort(key=lambda x: (-color_ranks.get(str(x["paint_seed"]), {}).get("BlueRatio", 0), x["paint_seed"]))
    else:
        skins.sort(key=lambda x: (x["paint_seed"], x["float"]))
    return skins

def toggle_display():
    global image_visible
    image_visible = not image_visible
    btn_toggle.config(text=f"IMG: {'ON' if image_visible else 'OFF'} (I)",
                      fg="green" if image_visible else "black")
    show_single()

def toggle_favorite():
    skins = get_sorted_skins()
    if not skins: return
    tpl_id = skins[current_index]["paint_seed"]
    if tpl_id in favorites:
        favorites.remove(tpl_id)
    else:
        favorites.append(tpl_id)
    with open(FAV_FILE, "w", encoding="utf-8") as f:
        json.dump(favorites, f)
    show_single()

def toggle_search():
    global search_window
    if search_window is None or not search_window.winfo_exists():
        search_window = tk.Toplevel(root)
        search_window.title("Search Seed")
        search_window.geometry(f"+{root.winfo_x()+50}+{root.winfo_y()+50}")

        tk.Label(search_window, text="Enter Template ID:").pack(padx=10, pady=5)
        entry = tk.Entry(search_window)
        entry.pack(padx=10, pady=5)
        entry.focus_set()

        def do_search(event=None):
            global current_index
            try:
                val = int(entry.get())
                skins = get_sorted_skins()
                for i, s in enumerate(skins):
                    if s["paint_seed"] == val:
                        current_index = i
                        show_single()
                        search_window.destroy()
                        return
                messagebox.showwarning("Not Found", "Seed not found.")
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number.")

        entry.bind("<Return>", do_search)
        search_window.bind("<KeyPress-s>", lambda e: search_window.destroy())
        search_window.bind("<KeyPress-S>", lambda e: search_window.destroy())
        tk.Button(search_window, text="Confirm", command=do_search).pack(pady=5)
    else:
        search_window.destroy()

def set_mode(m):
    global sort_mode, current_index
    sort_mode = m
    current_index = 0
    show_single()

# ====== 按钮布局 ======
btn_frame = tk.Frame(root)
btn_frame.pack(pady=10)

btn_toggle = tk.Button(btn_frame, text="IMG: OFF (I)", width=12, command=toggle_display)
btn_toggle.pack(side=tk.LEFT, padx=5)

tk.Button(btn_frame, text="Favorite (F)", width=10, command=toggle_favorite).pack(side=tk.LEFT, padx=2)
tk.Button(btn_frame, text="Search (S)", width=10, command=toggle_search).pack(side=tk.LEFT, padx=2)
tk.Button(btn_frame, text="Default (D)", width=10, command=lambda: set_mode(1)).pack(side=tk.LEFT, padx=2)
tk.Button(btn_frame, text="Green (G)", width=10, command=lambda: set_mode(2)).pack(side=tk.LEFT, padx=2)
tk.Button(btn_frame, text="Blue (B)", width=10, command=lambda: set_mode(3)).pack(side=tk.LEFT, padx=2)

# ====== 键盘交互 ======
def on_key(e):
    global current_index
    key = e.keysym.lower()

    if key == "left":
        current_index = (current_index - 1) % len(all_skins)
        show_single()
    elif key == "right":
        current_index = (current_index + 1) % len(all_skins)
        show_single()
    elif key == "i":
        toggle_display()
    elif key == "s":
        toggle_search()
    elif key == "f":
        toggle_favorite()
    elif key == "d":
        set_mode(1)
    elif key == "g":
        set_mode(2)
    elif key == "b":
        set_mode(3)

root.bind("<Key>", on_key)

show_single()
root.mainloop()