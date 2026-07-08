"""
配置持久化：保存在应用私有存储目录下的 config.json。
UI 线程和后台 Service 线程都读写这同一个文件，实现设置联动和状态回传。
"""
import json
import os

try:
    from android.storage import app_storage_path
    CONFIG_DIR = app_storage_path()
except Exception:
    CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".mycgc")

os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

# 已确认的合约地址（pair地址 0x4575De99337ccd0A63BF4e20A63BFd776e40e215）
DEFAULT_CONFIG = {
    "rpc_url": "https://rpc1.goodchainscan.org/",
    # 注意：用户 PowerShell 测试成功的地址是 0x4575De99337ccd0A63BF4e20A33BFd776e40e215
    # 原配置中是 A63B，这是一个拼写错误！
    "pair_address": "0x4575de99337ccd0a63bf4e20a33bfd776e40e215",
    "token_a": "0x1c7ca2f2a0de1ffcce397b539acda16e054ae348",  # WGDC (token0)
    "token_b": "0xdde17d5ef0cce745ce35f5ccd618b728fe7164ac",  # CGC (token1)
    "interval_minutes": 5,      # 需求一：刷新间隔（分钟），可任意设置
    "low_ratio": 90.0,          # 需求二 第2档：低于此值提醒 "GDC NOW LOW!"
    "high_ratio": 110.0,        # 需求二 第3档：高于此值提醒 "GDC NOW HAGH!"
    "last_ratio": None,         # 第1档：最近一次实时比例（CGC / WGDC）
    "last_cgc": None,
    "last_wgdc": None,
    "last_update": None,
    "service_running": False,
}


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(cfg)
            return merged
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    tmp_path = CONFIG_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, CONFIG_PATH)
