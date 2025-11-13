#!/usr/bin/env python3

import requests
import os
import sys

# 判断系统类型
windows = "win" in sys.platform

def grab(url):
    """从直播链接中提取m3u8流地址"""
    try:
        s = requests.Session()
        # 尝试获取页面内容（支持requests和curl）
        response = s.get(url, timeout=15).text
        if ".m3u8" not in response:
            response = requests.get(url).text
            if ".m3u8" not in response:
                if windows:
                    return None
                # 非Windows用curl重试
                os.system(f"curl '{url}' > temp.txt 2>/dev/null")
                if not os.path.exists("temp.txt"):
                    return None
                with open("temp.txt", "r", encoding="utf-8", errors="ignore") as f:
                    response = f.read()
                if ".m3u8" not in response:
                    return None
        
        # 定位m3u8链接
        end = response.find(".m3u8") + 5
        tuner = 100
        max_tuner = len(response)  # 避免无限循环
        while tuner <= max_tuner:
            if "https://" in response[end - tuner : end]:
                link = response[end - tuner : end]
                start = link.find("https://")
                end_pos = link.find(".m3u8") + 5
                m3u8_url = link[start:end_pos]
                # 提取高清流（最后一个流）
                streams = s.get(m3u8_url, timeout=15).text.split("#EXT")
                if len(streams) < 2:
                    return None
                hd_stream = streams[-1].strip()
                stream_start = hd_stream.find("http")
                if stream_start == -1:
                    return None
                return hd_stream[stream_start:].strip()
            tuner += 5
        return None  # 未找到有效流
    except Exception as e:
        print(f"处理链接 {url} 出错: {e}", file=sys.stderr)
        return None

def generate_combined_m3u8():
    """生成包含所有频道信息的合并m3u8文件"""
    input_txt = "/mnt/nvme0n1-4/youtube-to-m3u8/information/all_channels.txt"
    output_m3u8 = "/mnt/nvme0n1-4/youtube-to-m3u8/streams/all_streams.m3u8"
    
    with open(output_m3u8, "w", encoding="utf-8") as out_f:
        # m3u8标准头部
        out_f.write("#EXTM3U\n")
        
        with open(input_txt, "r", encoding="utf-8") as in_f:
            lines = [line.strip() for line in in_f if line.strip()]
            i = 0
            while i < len(lines):
                line = lines[i]
                # 跳过注释行
                if line.startswith("~~"):
                    i += 1
                    continue
                # 跳过分隔符
                if line == "------------":
                    i += 1
                    continue
                # 处理频道元信息行（非https开头）
                if not line.startswith("https://"):
                    # 按|分割元信息（频道名|分组|logo|tvg-id）
                    parts = [p.strip() for p in line.split("|")]
                    ch_name = parts[0] if len(parts) > 0 else "Unknown"
                    grp_title = parts[1] if len(parts) > 1 else "Uncategorized"
                    tvg_logo = parts[2] if len(parts) > 2 else ""
                    tvg_id = parts[3] if len(parts) > 3 else ""
                    # 下一行应为直播链接
                    i += 1
                    if i >= len(lines):
                        break
                    url = lines[i].strip()
                    if not url.startswith("https://"):
                        i += 1
                        continue
                    # 提取m3u8流
                    m3u8_link = grab(url)
                    if m3u8_link:
                        # 写入带元信息的m3u8条目（播放器可识别）
                        out_f.write(
                            f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{tvg_logo}" group-title="{grp_title}",{ch_name}\n'
                        )
                        out_f.write(f"{m3u8_link}\n")
                i += 1
    
    # 清理临时文件
    if os.path.exists("temp.txt"):
        os.remove("temp.txt")
    # 清理可能的残留文件
    for f in os.listdir("."):
        if f.startswith("watch"):
            os.remove(f)
    print(f"合并完成，输出文件：{output_m3u8}")

if __name__ == "__main__":
    generate_combined_m3u8()
