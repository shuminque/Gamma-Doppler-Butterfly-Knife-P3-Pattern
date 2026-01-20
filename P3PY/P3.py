import requests
from time import sleep
from tqdm import tqdm
import json
import os
from collections import defaultdict

# ====== 配置 ======
P3_DIR = r"C:\Users\Q\Desktop\P3"
OUTPUT_DIR = r"C:\Users\Q\Desktop"
SLEEP_TIME = 1          # 每次请求间隔（秒），建议 >=1
MAX_RETRIES = 5         # 最大重试次数
CACHE_FILE = os.path.join(OUTPUT_DIR, "success_cache.json")  # 已成功 paint_seed 缓存
FAILED_FILE = os.path.join(OUTPUT_DIR, "failed_paint_seeds.json")  # 失败记录

# ====== 读取所有 json ======
all_results = []
for i in range(1, 48):
    json_path = os.path.join(P3_DIR, f"{i}.json")
    if not os.path.exists(json_path):
        print(f"跳过不存在文件: {json_path}")
        continue

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        all_results.extend(data.get("results", []))

print(f"总共读取 {len(all_results)} 条 Phase 3 数据")

# ====== 读取已成功缓存 ======
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        success_cache = json.load(f)
else:
    success_cache = {}

failed_seeds = []

# ====== 按 paint_seed 分桶 ======
buckets = defaultdict(list)

for item in tqdm(all_results):
    paint_seed = str(item["paint_seed"])
    if paint_seed in success_cache:
        # 已经下载过，直接使用缓存
        buckets[int(paint_seed)//100].append(success_cache[paint_seed])
        continue

    sig = item["screenshot_sig"]
    inspect_url = item["serialized_inspect"]
    api_url = f"https://s-api.csfloat.com/api/v1/public/screenshot?sig={sig}&url={inspect_url}"

    wait_time = SLEEP_TIME
    success = False

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(api_url, timeout=10)
            if resp.status_code == 200:
                j = resp.json()
                playside = "https://csfloat.pics/" + j["sides"]["playside"]["path"] + "?v=3"
                backside = "https://csfloat.pics/" + j["sides"]["backside"]["path"] + "?v=3"

                item_data = {
                    "paint_seed": int(paint_seed),
                    "float": item["float_value"],
                    "playside": playside,
                    "backside": backside
                }

                # 保存到桶和缓存
                buckets[int(paint_seed)//100].append(item_data)
                success_cache[paint_seed] = item_data
                success = True
                sleep(wait_time)
                break
            elif resp.status_code == 429:
                print(f"[尝试 {attempt}] 请求被限流 paint_seed {paint_seed}, 等待 {wait_time:.1f}s")
                sleep(wait_time)
                wait_time *= 2  # 指数退避
            else:
                print(f"[尝试 {attempt}] 请求失败 paint_seed {paint_seed}, 状态码 {resp.status_code}")
                sleep(wait_time)
        except Exception as e:
            print(f"[尝试 {attempt}] 异常 paint_seed {paint_seed}: {e}")
            sleep(wait_time)
            wait_time *= 2

    if not success:
        print(f"❌ paint_seed {paint_seed} 超过 {MAX_RETRIES} 次仍然失败，跳过")
        failed_seeds.append(paint_seed)

    # 保存缓存文件（可中途停止，已完成部分不会丢）
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(success_cache, f, ensure_ascii=False, indent=2)
    with open(FAILED_FILE, "w", encoding="utf-8") as f:
        json.dump(failed_seeds, f, ensure_ascii=False, indent=2)

# ====== 生成 HTML ======
HTML_TEMPLATE_HEAD = """
<!DOCTYPE html>
<html>
<head>
<title>Gamma Doppler Phase 3 Gallery</title>
<style>
.grid { display: flex; flex-wrap: wrap; }
.card { margin: 5px; border: 1px solid #ccc; padding: 3px; width: 150px; }
img { width: 100%; }
.label { text-align: center; font-size: 12px; }
</style>
</head>
<body>
<h1>Gamma Doppler Phase 3 PaintSeed Gallery</h1>
<div class="grid">
"""

HTML_TEMPLATE_TAIL = """
</div>
</body>
</html>
"""

for bucket_index, skins in buckets.items():
    skins.sort(key=lambda x: x["paint_seed"])
    html_content = HTML_TEMPLATE_HEAD

    for s in skins:
        html_content += f"""
        <div class="card">
            <div class="label">
                PaintSeed: {s['paint_seed']}<br>
                Float: {s['float']:.6f}
            </div>
            <img src="{s['playside']}" alt="Playside">
            <img src="{s['backside']}" alt="Backside">
        </div>
        """

    html_content += HTML_TEMPLATE_TAIL
    html_path = os.path.join(OUTPUT_DIR, f"G3_gallery{bucket_index}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"生成完成：{html_path}")

print("✅ 全部处理完成")
print(f"失败 paint_seed 数量: {len(failed_seeds)}, 可在 {FAILED_FILE} 查看")
