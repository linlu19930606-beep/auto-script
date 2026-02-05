import requests
import base64
import re
import socket
import json
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# --- 配置区 ---
SOURCES = [
    "https://raw.githubusercontent.com/free-nodes/v2rayfree/main/v202602052",
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/main/all_extracted_configs.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/ss.txt"
]
MAX_THREADS = 30  # 线程数，30-50 比较高效
TIMEOUT = 2.5     # 节点连接超时时间（秒）

# --- 功能模块 ---

def fetch_raw_data(url):
    """抓取并初级解码"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            text = resp.text.strip()
            if "://" not in text:
                text += '=' * (4 - len(text) % 4)
                return base64.b64decode(text).decode('utf-8', errors='ignore')
            return text
    except:
        return ""
    return ""

def parse_ip_port(node):
    """从不同协议提取 IP 和端口"""
    try:
        if node.startswith('vmess://'):
            data = json.loads(base64.b64decode(node[8:] + '===').decode('utf-8'))
            return data.get('add'), data.get('port')
        parsed = urlparse(node)
        if parsed.hostname: return parsed.hostname, parsed.port
        match = re.search(r'@([^:]+):(\d+)', node)
        if match: return match.group(1), match.group(2)
    except: pass
    return None, None

def check_node(node):
    """测试节点通畅性"""
    ip, port = parse_ip_port(node)
    if not ip or not port: return None
    try:
        with socket.create_connection((str(ip), int(port)), timeout=TIMEOUT):
            return node
    except:
        return None

# --- 主程序流 ---

def start_workflow():
    start_time = time.time()
    print("🚀 [1/3] 正在全网搜集原始节点...")
    
    raw_pool = []
    for url in SOURCES:
        content = fetch_raw_data(url)
        found = re.findall(r'(?:ss|vmess|vless|trojan|ssr|hy2)://[^\s<>"]+', content)
        raw_pool.extend(found)
    
    unique_raw = list(set(raw_pool))
    print(f"✅ 搜集完成，共 {len(unique_raw)} 个唯一节点。")

    print(f"⚡ [2/3] 启动 {MAX_THREADS} 线程进行存活检测...")
    alive_nodes = []
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = [executor.submit(check_node, n) for n in unique_raw]
        for i, f in enumerate(as_completed(futures)):
            res = f.result()
            if res: alive_nodes.append(res)
            if (i+1) % 20 == 0:
                print(f"⏳ 已检测: {i+1}/{len(unique_raw)}", end='\r')

    print(f"\n✅ 检测完成！存活节点: {len(alive_nodes)}")

    print("📦 [3/3] 正在封装订阅文件...")
    if alive_nodes:
        sub_content = "\n".join(alive_nodes)
        encoded_sub = base64.b64encode(sub_content.encode('utf-8')).decode('utf-8')
        
        with open("my_subscribe.txt", "w", encoding="utf-8") as f:
            f.write(encoded_sub)
        
        # 同时保存一个明文版方便查看
        with open("alive_list.txt", "w", encoding="utf-8") as f:
            f.write(sub_content)
            
        print(f"\n✨ 全部任务已完成！耗时: {int(time.time()-start_time)}s")
        print(f"📂 订阅包已生成: my_subscribe.txt")
        print(f"📂 明文列表已生成: alive_list.txt")
    else:
        print("❌ 未发现可用节点，请检查网络或源地址。")

if __name__ == "__main__":
    start_workflow()
