import os
import requests
import time
import json
from bs4 import BeautifulSoup
from minecraft_versions import get_minecraft_versions
from rpv import local_rpv


def download(url: str, timeout: int = 6, retries: int = 4) -> str:
    attempt = 0
    last_exception = None

    while attempt <= retries:
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text

        except requests.exceptions.RequestException as e:
            last_exception = e
            attempt += 1
            if attempt > retries:
                break
            wait_time = 1.0 * (2 ** (attempt - 1))  # 从 1s 开始更稳
            print(f"[重试 {attempt}/{retries}] 等待 {wait_time:.1f}s...")
            print(f"    错误: {e}")
            time.sleep(wait_time)

    raise last_exception or requests.exceptions.RequestException("下载失败")


def main():
    # 创建输出目录
    os.makedirs("download", exist_ok=True)
    os.makedirs("output", exist_ok=True)

    # 1. 下载版本清单
    try:
        print("正在下载 Minecraft 版本清单...")
        version_manifest_json = download(
            "https://piston-meta.mojang.com/mc/game/version_manifest.json"
        )
    except requests.exceptions.RequestException as e:
        print(f"无法获取版本清单: {e}")
        return

    # 2. 获取最新版本号
    try:
        version_manifest_json = json.loads(version_manifest_json)
        minecraft_versions = get_minecraft_versions(version_manifest_json)
        if not minecraft_versions:
            print("未找到任何 Minecraft 版本")
            return
        mcv = minecraft_versions[0]  # 最新版本
        print(f"最新版本: {mcv}")
    except Exception as e:
        print(f"解析版本清单失败: {e}")
        return

    # 3. 下载 Wiki 页面
    wiki_url = f"https://minecraft.wiki/w/Java_Edition_{mcv.replace(' ', '_')}"
    try:
        print(f"正在访问 Wiki 页面: {wiki_url}")
        wiki_html = download(wiki_url)
    except requests.exceptions.RequestException as e:
        print(f"无法获取 Wiki 页面: {e}")
        return

    # 4. 解析 Resource Pack 和 Data Pack 版本
    soup = BeautifulSoup(wiki_html, "html.parser")
    v = {"rp": "0", "dp": "0"}

    for tr in soup.find_all("tr"):
        th = tr.find("th")
        td = tr.find("td")
        if not (th and td):
            continue

        label = th.get_text(strip=True)
        value = td.get_text(strip=True).split("[")[0].strip()  # 去掉引用标记

        if "Resource pack format" in label:
            v["rp"] = value
        elif "Data pack format" in label:
            v["dp"] = value

    # 5. 输出结果
    print("---------------------------------------")
    print("Minecraft Version:     ", mcv)
    print("Resourcepack Version:  ", v["rp"])
    print("Datapack Version:      ", v["dp"])
    print("---------------------------------------")

    # 6. 写入文件
    rpv = {mcv: v["rp"], **local_rpv}
    with open("output/rp_version.json", "w", encoding="utf-8") as f:
        json.dump(rpv, f, indent=4, ensure_ascii=False)

    with open("output/mcv.txt", "w", encoding="utf-8") as f:
        f.write(mcv + "\n")

    print("结果已保存至 output/ 目录")


if __name__ == "__main__":
    main()
