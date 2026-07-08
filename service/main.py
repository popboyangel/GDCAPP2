"""
后台前台服务（foreground service）：
- 息屏也持续运行（需求三），配合 buildozer.spec 里的 WAKE_LOCK / FOREGROUND_SERVICE 权限
- 每隔 cfg['interval_minutes'] 分钟刷新一次链上数据（需求一）
- 计算 CGC/WGDC 实时比例，与用户设置的第2档(低)、第3档(高)阈值比较，触发通知（需求二）

每轮循环都会重新读取 config.json，所以用户在 UI 里改了间隔或阈值，
下一轮循环就会生效，不需要重启服务。
"""
import os
import sys
import time
import traceback

# 让这个 service 进程也能 import 到项目根目录下的共享模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_store import load_config, save_config  # noqa: E402
from monitor_core import fetch_amounts_and_ratio  # noqa: E402
from notify import send_notification  # noqa: E402

try:
    from jnius import autoclass
    PythonService = autoclass("org.kivy.android.PythonService")
    Context = autoclass("android.content.Context")
    PowerManager = autoclass("android.os.PowerManager")
    
    # 尝试获取唤醒锁
    service = PythonService.mService
    service.setAutoRestartService(True)
    
    pm = service.getSystemService(Context.POWER_SERVICE)
    # PARTIAL_WAKE_LOCK = 1
    wake_lock = pm.newWakeLock(1, "MyCGC::MonitorWakeLock")
    wake_lock.acquire()

    # 绑定为真正的前台服务，防止被系统杀掉
    try:
        NotificationManager = autoclass("android.app.NotificationManager")
        NotificationChannel = autoclass("android.app.NotificationChannel")
        Builder = autoclass("android.app.Notification$Builder")
        Build_VERSION = autoclass("android.os.Build$VERSION")
        
        channel_id = "mycgc_fg_channel"
        if Build_VERSION.SDK_INT >= 26:
            # 前台服务通知不需要很高优先级，避免打扰用户，只需要保持存活
            channel = NotificationChannel(channel_id, "MyCGC 后台运行", NotificationManager.IMPORTANCE_LOW)
            ns = service.getSystemService(Context.NOTIFICATION_SERVICE)
            ns.createNotificationChannel(channel)
            builder = Builder(service, channel_id)
        else:
            builder = Builder(service)
            
        builder.setContentTitle("MyCGC 正在后台监控")
        builder.setContentText("保持此通知以确保息屏刷新正常工作")
        try:
            icon = service.getApplicationInfo().icon
            builder.setSmallIcon(icon)
        except:
            pass
            
        notification = builder.build()
        # 调用 startForeground(id, notification)
        service.startForeground(1998, notification)
    except Exception as fg_e:
        print("startForeground failed:", fg_e)

except Exception as e:
    print("WakeLock acquire failed:", e)
    wake_lock = None

def main_loop():
    while True:
        interval_minutes = 5
        try:
            cfg = load_config()
            interval_minutes = max(1, int(cfg.get("interval_minutes", 5)))

            cgc, wgdc, ratio = fetch_amounts_and_ratio(cfg)

            cfg["last_cgc"] = cgc
            cfg["last_wgdc"] = wgdc
            cfg["last_ratio"] = ratio
            cfg["last_update"] = time.time()
            cfg["service_running"] = True
            save_config(cfg)

            low_ratio = float(cfg.get("low_ratio", 0))
            high_ratio = float(cfg.get("high_ratio", 0))

            if ratio is not None:
                if ratio < low_ratio:
                    send_notification("MyCGC 提醒", "GDC NOW LOW!")
                elif ratio > high_ratio:
                    send_notification("MyCGC 提醒", "GDC NOW HAGH!")

        except Exception:
            traceback.print_exc()

        # 使用时间戳校验来休眠，防止系统休眠导致的 time.sleep 漂移
        sleep_seconds = interval_minutes * 60
        target_time = time.time() + sleep_seconds
        
        while time.time() < target_time:
            # 每次最多睡 10 秒，醒来检查一下配置是否被前台改了（可选），或者单纯防挂起
            time.sleep(min(10, target_time - time.time()))


if __name__ == "__main__":
    try:
        main_loop()
    finally:
        if 'wake_lock' in globals() and wake_lock:
            try:
                wake_lock.release()
            except:
                pass
