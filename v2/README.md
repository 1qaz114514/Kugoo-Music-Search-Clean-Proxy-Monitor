# 🎵 酷狗音乐拦截工具

一个高效的酷狗音乐搜索拦截工具，支持白名单模式和额外关键词拦截，可后台静默运行。

## 📥 下载

**最新版本**: [ku v2.exe](https://github.com/1qaz114514/Kugoo-Music-Search-Clean-Proxy-Monitor/releases/latest/download/ku%20v2.exe)

## ✨ 功能特性

### 🎯 核心功能
- **白名单模式**: 只放行白名单中的歌手和歌曲
- **额外拦截**: 自动拦截包含 `91` 或 `78` 的搜索词（如 9178、7891、91xx、xx78 等）
- **进程监控**: 实时监控酷狗音乐进程状态

### 🔧 技术特性
- **后台静默运行**: 隐藏所有窗口，任务栏无图标
- **开机自启动**: 每次启动自动检测并添加开机自启动
- **日志记录**: 日志保存到 `C:\KuGouFilterLogs\`
- **CA证书自动安装**: 自动处理SSL证书

### 🛡️ 拦截规则
| 搜索词 | 是否拦截 | 原因 |
|--------|---------|------|
| 周杰伦 | ✅ 放行 | 在白名单中 |
| 9178 | ❌ 拦截 | 包含91和78 |
| 7891 | ❌ 拦截 | 包含91和78 |
| 91测试 | ❌ 拦截 | 包含91 |
| 测试78 | ❌ 拦截 | 包含78 |
| 其他歌手 | ❌ 拦截 | 不在白名单中 |

## 🚀 使用方法

### 1. 运行程序
双击 `ku v2.exe` 运行程序

### 2. 配置酷狗代理
1. 打开酷狗音乐
2. 进入设置 → 代理设置
3. 配置代理为：`127.0.0.1:8080`
4. 重启酷狗音乐

### 3. 白名单配置
编辑 `config/singer_whitelist.txt` 和 `config/song_whitelist.txt` 添加白名单：

```
# 歌手白名单示例
周杰伦
林俊杰
陈奕迅

# 歌曲白名单示例（可选）
晴天
江南
十年
```

## 📁 目录结构

```
v2/
├── dist/                    # 打包输出目录
│   └── ku v2.exe           # 最终可执行文件
├── src/                     # 源代码
│   ├── kugou_launcher_v2.py    # 发行版主程序
│   ├── kugou_launcher_debug.py  # 调错版主程序
│   ├── kugou_filter.py         # 拦截过滤器
│   ├── kugou_config.py         # 配置文件
│   └── kugou_ssl_bypass.js     # SSL绕过脚本
├── config/                  # 配置目录
│   ├── singer_whitelist.txt    # 歌手白名单
│   └── song_whitelist.txt      # 歌曲白名单
├── requirements.txt         # Python依赖
└── build.bat               # 打包脚本
```

## 🔨 从源码构建

### 环境要求
- Python 3.11+
- Windows 10/11

### 构建步骤
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行打包脚本
build.bat
```

### 手动打包
```bash
pyinstaller --clean build_v2.spec
```

## 📝 日志位置

日志文件位于：`C:\KuGouFilterLogs\`

日志文件名格式：`kugou_launcher_YYYYMMDD_HHMMSS.log`

## ⚠️ 注意事项

1. **首次运行需要管理员权限**（用于安装CA证书和设置开机自启动）
2. **必须配置酷狗代理**才能正常拦截
3. **白名单需要完全匹配**才会放行
4. **包含91或78的搜索词会被自动拦截**

## 🐛 问题排查

### 拦截无效
- 检查酷狗音乐是否已配置代理 `127.0.0.1:8080`
- 检查日志文件查看拦截记录
- 确保程序正在运行

### 酷狗无法启动
- 可能frida注入导致，尝试使用调错版查看详细日志

## 📄 许可证

本项目仅供学习和研究使用。

## 🙏 致谢

- [mitmproxy](https://mitmproxy.org/) - 强大的代理工具
- [psutil](https://github.com/giampaolo/psutil) - 进程监控
