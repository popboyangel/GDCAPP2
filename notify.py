"""
直接用 pyjnius 调用 Android NotificationManager 发通知。
这样比 plyer 更适合在无界面的后台 Service 里使用，也不依赖 Activity 存活。
"""
import time


def send_notification(title, message):
    try:
        from jnius import autoclass

        Context = autoclass("android.content.Context")
        NotificationManager = autoclass("android.app.NotificationManager")
        NotificationChannel = autoclass("android.app.NotificationChannel")
        Builder = autoclass("android.app.Notification$Builder")
        Build_VERSION = autoclass("android.os.Build$VERSION")

        context = None
        try:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            context = PythonActivity.mActivity
        except Exception:
            context = None

        if context is None:
            try:
                PythonService = autoclass("org.kivy.android.PythonService")
                context = PythonService.mService
            except Exception:
                context = None

        if context is None:
            print("notify: 找不到有效的 Android context")
            return

        ns = context.getSystemService(Context.NOTIFICATION_SERVICE)
        channel_id = "mycgc_channel"

        if Build_VERSION.SDK_INT >= 26:
            channel = NotificationChannel(
                channel_id, "MyCGC 提醒", NotificationManager.IMPORTANCE_HIGH
            )
            # 允许在锁屏显示
            channel.setLockscreenVisibility(1) # VISIBILITY_PUBLIC
            ns.createNotificationChannel(channel)
            builder = Builder(context, channel_id)
        else:
            builder = Builder(context)
            # 旧版本设置优先级
            builder.setPriority(2) # PRIORITY_MAX

        builder.setContentTitle(title)
        builder.setContentText(message)
        builder.setAutoCancel(True)
        try:
            icon = context.getApplicationInfo().icon
            builder.setSmallIcon(icon)
        except Exception:
            pass

        notif_id = int(time.time()) % 100000
        ns.notify(notif_id, builder.build())
    except Exception as e:
        print("notify error:", e)
