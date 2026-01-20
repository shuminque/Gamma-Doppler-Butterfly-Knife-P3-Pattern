import cv2
import numpy as np
import os
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed

# -----------------------
# 设置参数
# -----------------------
base_path = r"C:\Users\Q\Desktop\P3read\images"

# HSV范围
lower_green = np.array([35, 50, 50])
upper_green = np.array([85, 255, 255])

lower_blue = np.array([100, 50, 50])
upper_blue = np.array([140, 255, 255])

# -----------------------
# 定义颜色占比函数
# -----------------------
def color_ratio(img_path, lower_hsv, upper_hsv):
    """
    返回图像某颜色占比和模板号
    """
    filename = os.path.basename(img_path)
    template_id = filename.split("_")[0]

    img = cv2.imread(img_path)
    if img is None:
        return template_id, 0.0

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_hsv, upper_hsv)

    color_pixels = np.sum(mask > 0)
    total_pixels = mask.size
    ratio = color_pixels / total_pixels

    return template_id, ratio

# -----------------------
# 收集所有 playside 图片路径
# -----------------------
img_paths = []
for folder in map(str, range(10)):
    folder_path = os.path.join(base_path, folder)
    if not os.path.exists(folder_path):
        continue
    for f in os.listdir(folder_path):
        if "playside" in f:
            img_paths.append(os.path.join(folder_path, f))

# -----------------------
# 并行计算颜色占比
# -----------------------
def compute_ratios(paths, lower_hsv, upper_hsv):
    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_path = {executor.submit(color_ratio, p, lower_hsv, upper_hsv): p for p in paths}
        for future in as_completed(future_to_path):
            template_id, ratio = future.result()
            results.append((template_id, ratio))
    # 按占比降序排序
    results.sort(key=lambda x: x[1], reverse=True)
    return results

green_results = compute_ratios(img_paths, lower_green, upper_green)
blue_results = compute_ratios(img_paths, lower_blue, upper_blue)

# -----------------------
# 构建排名字典
# -----------------------
green_rank_dict = {tpl: rank for rank, (tpl, _) in enumerate(green_results, 1)}
blue_rank_dict = {tpl: rank for rank, (tpl, _) in enumerate(blue_results, 1)}

# -----------------------
# 输出到 CSV
# -----------------------
csv_file = os.path.join(base_path, "color_ratio_ranking.csv")
with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    # 列名英文
    writer.writerow(["TemplateID", "GreenRatio", "BlueRatio", "GreenRank", "BlueRank"])
    for tpl in green_rank_dict:
        green_ratio = dict(green_results)[tpl]
        blue_ratio = dict(blue_results).get(tpl, 0)
        green_rank = green_rank_dict[tpl]
        blue_rank = blue_rank_dict.get(tpl, 0)
        writer.writerow([tpl, f"{green_ratio:.4f}", f"{blue_ratio:.4f}", green_rank, blue_rank])

print(f"结果已保存到 {csv_file}")
