# MyCGC Monitor

监控 GoodChain DEX 上 CGC / WGDC 的储备比例，息屏也能后台跑，触发阈值自动发通知。

- Pair 合约: `0x4575De99337ccd0A63BF4e20A63BFd776e40e215`
- RPC 节点: `https://rpc1.goodchainscan.org/`
- token_a (WGDC): `0x1c7ca2f2a0de1ffcce397b539acda16e054ae348`
- token_b (CGC): `0xdde17d5ef0cce745ce35f5ccd618b728fe7164ac`

## 三个需求对应实现

1. **定时刷新计算比例**：`service/main.py` 后台循环，间隔由 `interval_minutes` 决定，随时可在 App 里改。
2. **3档比例 + 双向提醒**：
   - 第1档 = 实时 `CGC / WGDC`
   - 第2档 = 你设的低阈值，第1档 < 第2档 → 通知 "GDC NOW LOW!"
   - 第3档 = 你设的高阈值，第1档 > 第3档 → 通知 "GDC NOW HAGH!"
3. **息屏不影响监控**：用 Android 前台服务（foreground service）+ `WAKE_LOCK` 权限实现，务必在 App 里点"关闭电池优化"，否则国产系统/原生Android仍可能把服务杀掉。

## 打包步骤（本地没有Android SDK，用GitHub Actions云端编译）

1. 把这个项目推到你自己的 GitHub 仓库（新建仓库或用你已有的 mycgc 仓库）：
   ```bash
   cd mycgc2
   git init
   git add .
   git commit -m "init mycgc monitor"
   git branch -M main
   git remote add origin <你的仓库地址>
   git push -u origin main
   ```
2. 推送后自动触发 `.github/workflows/build.yml`，在 GitHub 仓库的 **Actions** 标签页可以看到构建进度（大约10-20分钟，第一次会比较慢）。
3. 构建成功后，在该次 workflow run 页面的 **Artifacts** 里下载 `mycgc-apk`，里面是 `.apk` 文件。
4. 把 apk 传到手机上安装（需要允许"安装未知来源应用"）。

## 安装后使用

1. 打开 App，先设置：刷新间隔（分钟）、第2档低阈值、第3档高阈值，点"保存设置"。
2. 点"关闭电池优化"，系统会弹窗，选择"允许"/"不限制"。
3. 点"启动后台监控"。可以退到后台或息屏，服务会按你设的间隔持续跑。
4. 触发阈值时手机会收到通知："GDC NOW LOW!" 或 "GDC NOW HAGH!"。
5. 想手动看一眼当前比例，点"立即刷新一次"，界面上会显示 CGC/WGDC 数量和比例。

## 已知注意事项

- 首次运行 Android 13+ 系统会弹窗要通知权限，务必允许，否则收不到提醒。
- 部分手机品牌（小米/华为/OPPO/vivo等）即使关了系统电池优化，还有自己的"应用自启动/后台管理"开关，建议额外去手机设置里给这个 App 单独开自启动、后台运行权限。
- 如果 RPC 节点偶尔超时，当次刷新会在日志里打印异常但不会让服务崩溃，下一轮会自动重试。
