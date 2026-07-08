[app]
title = MyCGC Monitor
package.name = mycgc
package.domain = org.dahai.mycgc
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf,otf
version = 1.0

requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.0,pyjnius,requests,certifi

orientation = portrait
fullscreen = 0

# 息屏也要能持续跑：需要 FOREGROUND_SERVICE + WAKE_LOCK
# 通知：POST_NOTIFICATIONS（Android 13+ 需要动态申请）
# RECEIVE_BOOT_COMPLETED 预留给以后做"开机自启"用
android.permissions = INTERNET,FOREGROUND_SERVICE,WAKE_LOCK,POST_NOTIFICATIONS,RECEIVE_BOOT_COMPLETED

android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True
android.enable_androidx = True
android.archs = arm64-v8a

# 后台前台服务：对应 service/main.py，类名会是 Service + Monitor.capitalize() = ServiceMonitor
services = monitor:service/main.py

[buildozer]
log_level = 2
warn_on_root = 1
