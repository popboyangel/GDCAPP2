"""
MyCGC 监控 App 主界面（Kivy）。

功能：
- 显示第1档：实时 CGC / WGDC 数量与比例
- 设置刷新间隔分钟数（需求一）
- 设置第2档（低阈值）、第3档（高阈值）（需求二）
- 启动/停止后台前台服务（需求三，息屏也监控）
- 请求通知权限 & 引导用户关闭电池优化，避免系统杀掉后台服务
"""
import os
import threading
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.text import LabelBase, DEFAULT_FONT
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle

from config_store import load_config, save_config
from monitor_core import fetch_amounts_and_ratio

SERVICE_ENTRY_NAME = "monitor"  # 对应 buildozer.spec 里 services = monitor:service/main.py

# ---------------------------------------------------------------------------
# 注册中文字体为默认字体。必须在任何 Label/Button/TextInput 创建之前执行，
# 否则中文会因为默认的 Roboto 字体没有中文字形而显示成方块乱码。
# 字体文件需要你自己下载放到 assets/fonts/NotoSansSC-Regular.ttf
# （Google Noto Sans SC，免费商用：https://fonts.google.com/noto/specimen/Noto+Sans+SC）
# ---------------------------------------------------------------------------
_FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts", "NotoSansSC-Regular.ttf")
if os.path.exists(_FONT_PATH):
    LabelBase.register(DEFAULT_FONT, _FONT_PATH)
else:
    print(f"[WARN] 中文字体文件不存在: {_FONT_PATH}，中文会显示为方块乱码！")

# 统一配色，暗色主题
BG_COLOR = (0.07, 0.07, 0.09, 1)
CARD_COLOR = (0.14, 0.14, 0.17, 1)
ACCENT_COLOR = (0.20, 0.55, 0.95, 1)
TEXT_COLOR = (0.92, 0.92, 0.92, 1)


def _wrap_label(label):
    """让 Label 根据自身宽度自动换行，而不是超出高度溢出到相邻控件上。"""
    label.bind(size=lambda w, *_: setattr(w, "text_size", (w.width, None)))
    label.bind(texture_size=lambda w, *_: setattr(w, "height", max(w.texture_size[1] + dp(12), dp(40))))


class SectionLabel(Label):
    """带背景色的小标题，用来分隔每个设置区块，比纯文字更容易区分层级。"""

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(40))
        kwargs.setdefault("font_size", "15sp")
        kwargs.setdefault("halign", "left")
        kwargs.setdefault("valign", "middle")
        kwargs.setdefault("color", TEXT_COLOR)
        kwargs.setdefault("padding", (dp(10), 0))
        super().__init__(**kwargs)
        _wrap_label(self)
        with self.canvas.before:
            Color(*CARD_COLOR)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size


def make_input(text, input_filter):
    ti = TextInput(
        text=text,
        input_filter=input_filter,
        multiline=False,
        size_hint_y=None,
        height=dp(52),
        font_size="20sp",
        padding=(dp(12), dp(12)),
    )
    return ti


def make_button(text, accent=False):
    btn = Button(
        text=text,
        size_hint_y=None,
        height=dp(56),
        font_size="16sp",
        background_normal="",
        background_color=ACCENT_COLOR if accent else CARD_COLOR,
        color=(1, 1, 1, 1),
    )
    return btn


class MyCGCApp(App):
    def build(self):
        self.cfg = load_config()
        self.title = "MyCGC 监控"

        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        with root.canvas.before:
            Color(*BG_COLOR)
            self._root_bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda w, *_: setattr(self._root_bg, "pos", w.pos))
        root.bind(size=lambda w, *_: setattr(self._root_bg, "size", w.size))

        # ---- 顶部状态卡片 ----
        self.status_label = Label(
            text="尚未刷新",
            font_size="17sp",
            size_hint_y=None,
            height=dp(110),
            halign="left",
            valign="top",
            color=TEXT_COLOR,
            padding=(dp(12), dp(12)),
        )
        self.status_label.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        with self.status_label.canvas.before:
            Color(*CARD_COLOR)
            self._status_bg = Rectangle(pos=self.status_label.pos, size=self.status_label.size)
        self.status_label.bind(pos=lambda w, *_: setattr(self._status_bg, "pos", w.pos))
        self.status_label.bind(size=lambda w, *_: setattr(self._status_bg, "size", w.size))
        root.add_widget(self.status_label)

        # ---- 中间设置表单（可滚动，占满剩余空间） ----
        form = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))

        form.add_widget(SectionLabel(text="需求一：刷新间隔（分钟，可任意设置）"))
        self.interval_input = make_input(str(self.cfg.get("interval_minutes", 5)), "int")
        form.add_widget(self.interval_input)

        form.add_widget(SectionLabel(text="需求二 · 第2档低阈值：实时比例 < 此值 → 提醒 GDC NOW LOW!"))
        self.low_input = make_input(str(self.cfg.get("low_ratio", 90)), "float")
        form.add_widget(self.low_input)

        form.add_widget(SectionLabel(text="需求二 · 第3档高阈值：实时比例 > 此值 → 提醒 GDC NOW HAGH!"))
        self.high_input = make_input(str(self.cfg.get("high_ratio", 110)), "float")
        form.add_widget(self.high_input)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(form)
        root.add_widget(scroll)

        # ---- 底部按钮区 ----
        btn_row1 = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(10))
        save_btn = make_button("保存设置", accent=True)
        save_btn.bind(on_press=self.save_settings)
        refresh_btn = make_button("立即刷新一次")
        refresh_btn.bind(on_press=self.manual_refresh)
        btn_row1.add_widget(save_btn)
        btn_row1.add_widget(refresh_btn)
        root.add_widget(btn_row1)

        btn_row2 = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(10))
        start_btn = make_button("启动后台监控", accent=True)
        start_btn.bind(on_press=self.start_service)
        stop_btn = make_button("停止后台监控")
        stop_btn.bind(on_press=self.stop_service)
        btn_row2.add_widget(start_btn)
        btn_row2.add_widget(stop_btn)
        root.add_widget(btn_row2)

        battery_btn = make_button("关闭电池优化（息屏监控必须点这个）")
        battery_btn.bind(on_press=self.request_ignore_battery_optimization)
        root.add_widget(battery_btn)

        self.request_runtime_permissions()
        Clock.schedule_interval(self.refresh_status_label, 5)

        # 如果字体文件不存在，在界面上提示用户
        if not os.path.exists(_FONT_PATH):
            Clock.schedule_once(lambda dt: self.set_status_text("警告：未发现中文字体文件\n请确保 assets/fonts/ 目录下有字体文件"), 1)
            
        return root

    # ---------- 权限相关 ----------
    def request_runtime_permissions(self):
        try:
            from android.permissions import request_permissions, Permission
            perms = [Permission.INTERNET]
            for name in ("POST_NOTIFICATIONS",):
                p = getattr(Permission, name, None)
                if p:
                    perms.append(p)
            request_permissions(perms)
        except Exception:
            pass

    def request_ignore_battery_optimization(self, instance):
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            Settings = autoclass("android.provider.Settings")
            Uri = autoclass("android.net.Uri")
            activity = PythonActivity.mActivity
            intent = Intent()
            intent.setAction(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
            intent.setData(Uri.parse("package:" + activity.getPackageName()))
            activity.startActivity(intent)
        except Exception as e:
            self.status_label.text = f"请求电池优化白名单失败: {e}"

    # ---------- 设置 ----------
    def save_settings(self, instance):
        try:
            # 更新内存中的配置
            self.cfg["interval_minutes"] = int(self.interval_input.text)
            self.cfg["low_ratio"] = float(self.low_input.text)
            self.cfg["high_ratio"] = float(self.high_input.text)
            # 保存到文件
            save_config(self.cfg)
            # 重新加载一次以确保同步（虽然 self.cfg 已经更新，但这样更稳妥）
            self.cfg = load_config()
            self.status_label.text = "设置已保存"
        except Exception as e:
            self.status_label.text = f"保存失败: {e}"

    # ---------- 服务启停 ----------
    def start_service(self, instance):
        self.save_settings(instance)
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            activity = PythonActivity.mActivity
            service_class = activity.getPackageName() + ".Service" + SERVICE_ENTRY_NAME.capitalize()
            intent = Intent()
            intent.setClassName(activity.getPackageName(), service_class)
            activity.startService(intent)
            self.cfg["service_running"] = True
            save_config(self.cfg)
            self.status_label.text = "后台监控已启动"
        except Exception as e:
            self.status_label.text = f"启动失败: {e}"

    def stop_service(self, instance):
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            activity = PythonActivity.mActivity
            service_class = activity.getPackageName() + ".Service" + SERVICE_ENTRY_NAME.capitalize()
            intent = Intent()
            intent.setClassName(activity.getPackageName(), service_class)
            activity.stopService(intent)
            self.cfg["service_running"] = False
            save_config(self.cfg)
            self.status_label.text = "后台监控已停止"
        except Exception as e:
            self.status_label.text = f"停止失败: {e}"

    # ---------- 手动刷新 / 状态展示 ----------
    def manual_refresh(self, instance):
        self.status_label.text = "刷新中..."
        threading.Thread(target=self._do_manual_refresh, daemon=True).start()

    def _do_manual_refresh(self):
        try:
            cgc, wgdc, ratio = fetch_amounts_and_ratio(self.cfg)
            self.cfg["last_cgc"] = cgc
            self.cfg["last_wgdc"] = wgdc
            self.cfg["last_ratio"] = ratio
            self.cfg["last_update"] = time.time()
            save_config(self.cfg)
            # 刷新完成后，强制 UI 线程立即更新一次标签
            Clock.schedule_once(lambda dt: self.refresh_status_label(0))
        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            print("manual refresh error:", err_msg)
            Clock.schedule_once(lambda dt: self.set_status_text(f"刷新失败: {str(e)}"))

    def set_status_text(self, text):
        self.status_label.text = text

    def refresh_status_label(self, dt):
        cfg = load_config()
        ratio = cfg.get("last_ratio")
        cgc = cfg.get("last_cgc")
        wgdc = cfg.get("last_wgdc")
        ts = cfg.get("last_update")
        if ratio is not None and cgc is not None and wgdc is not None:
            t_str = time.strftime("%H:%M:%S", time.localtime(ts)) if ts else "-"
            self.status_label.text = (
                f"CGC: {cgc:.4f}   WGDC: {wgdc:.4f}\n"
                f"实时比例(第1档): {ratio:.4f}\n"
                f"更新于 {t_str}"
            )


if __name__ == "__main__":
    MyCGCApp().run()
