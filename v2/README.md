# 酷狗音乐拦截脚本 V2

酷狗音乐广告和推荐内容拦截工具，支持开机自启动和进程监控。

## 目录结构

```
v2/
├── src/                    # 源代码目录
│   ├── kugou_config.py    # 配置文件
│   ├── kugou_filter.py    # 拦截过滤器
│   ├── kugou_ssl_bypass.js # SSL绕过脚本
│   ├── kugou_launcher_debug.py  # 调错版启动器
│   └── kugou_launcher_v2.py     # 发行V2版启动器
├── config/                 # 配置文件目录
│   ├── singer_whitelist.txt  # 歌手白名单
│   └── song_whitelist.txt    # 歌曲白名单
├── dist/                   # 输出目录（打包后的exe）
├── build/                  # 构建临时目录
├── build_debug.spec        # 调错版打包配置
├── build_v2.spec           # 发行V2版打包配置
├── build.bat               # 打包脚本
└── requirements.txt        # Python依赖
```

## 版本说明

### 调错版 (kugou debug.exe)
- 保持所有命令行窗口可见
- 保留完整的控制台输出信息
- 提供交互式菜单选择功能
- 适合开发调试使用

### 发行V2版 (ku v2.exe)
- 隐藏所有窗口，后台静默运行
- 增强容错能力和异常捕获
- 优化资源释放机制
- 自动添加到开机自启动
- 适合日常使用

## 功能特性

1. **开机自动启动**
   - 自动添加到系统启动项
   - 系统启动后自动运行

2. **酷狗进程监控**
   - 实时检测酷狗音乐进程
   - 新进程创建后立即自动注入
   - 支持多酷狗进程同时监控

3. **广告拦截**
   - 拦截酷狗音乐各类广告
   - 拦截推荐内容
   - 支持白名单配置

4. **高稳定性**
   - 进程异常自动重启
   - 完善的异常处理
   - 资源自动释放

## 使用方法

### 调错版
1. 双击运行 `kugou debug.exe`
2. 根据菜单选择功能：
   - 1: 启动拦截器（默认）
   - 2: 启用开机自动启动
   - 3: 禁用开机自动启动
   - 4: 检查开机启动状态

### 发行V2版
1. 双击运行 `ku v2.exe`
2. 程序会自动：
   - 添加到开机自启动
   - 隐藏窗口后台运行
   - 开始监控酷狗进程

#### 命令行参数
- `--enable-startup`: 启用开机自启动
- `--disable-startup`: 禁用开机自启动
- `--check-startup`: 检查开机启动状态

## 白名单配置

编辑 `config/` 目录下的白名单文件：

- `singer_whitelist.txt`: 歌手白名单，每行一个歌手名
- `song_whitelist.txt`: 歌曲白名单，每行一个歌曲名

## 开发与打包

### 环境准备
```bash
pip install -r requirements.txt
```

### 打包
```bash
build.bat
```

打包后的可执行文件位于 `dist/` 目录。

## 日志文件

日志文件默认保存在：
- `C:\KuGouFilterLogs\`
- 或用户目录下的 `KuGouFilterLogs\`

## 注意事项

1. 需要管理员权限运行
2. 首次使用需要安装 mitmproxy 证书
3. 建议将程序放在固定位置后再设置开机自启动

## 技术支持

如有问题请查看日志文件获取详细信息。
