# -*- coding: utf-8 -*-
"""
酷狗音乐拦截启动器 (调错版)
- 保持所有窗口可见
- 保留完整的控制台输出
- 增强：开机自动启动、酷狗进程监控
"""
import os
import sys
import time
import shutil
import socket
import subprocess
import psutil
import ctypes
import winreg
import traceback
import threading
from datetime import datetime
from typing import Optional, Tuple, Any

try:
    import win32gui
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


LOG_DIR = r"C:\KuGouFilterLogs"
LOG_FILE = None
DEFAULT_MITM_PORT = 8080
MAX_RETRY_COUNT = 5
RETRY_DELAY = 2
MAX_CONSECUTIVE_FAILURES = 10
PROCESS_MONITOR_INTERVAL = 2
HEALTH_CHECK_INTERVAL = 30
RUNTIME_DIR_NAME = "KuGouHijackRuntime"
INTERNAL_MITMDUMP_FLAG = "--internal-mitmdump"
INTERNAL_FRIDA_FLAG = "--internal-frida"


def safe_execute(func, default=None, log_error=True, max_retries=1, retry_delay=0.5, *args, **kwargs):
    last_exception = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if log_error:
                safe_log(f"安全执行异常 (尝试 {attempt + 1}/{max_retries}): {func.__name__} - {e}", "ERROR")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    return default


def safe_log(message: str, level: str = "INFO") -> None:
    global LOG_FILE
    try:
        if not LOG_FILE:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}\n"
        with open(LOG_FILE, 'a', encoding='utf-8', errors='replace') as f:
            f.write(log_line)
    except Exception:
        pass


def safe_print(message: str, prefix: str = "") -> None:
    try:
        if prefix:
            print(f"{prefix}{message}")
        else:
            print(message)
    except Exception:
        pass


def init_logger() -> bool:
    global LOG_FILE
    try:
        log_dirs = [
            LOG_DIR,
            os.path.join(os.path.expanduser("~"), "KuGouFilterLogs"),
            os.path.join(os.getcwd(), "logs"),
        ]
        
        log_dir = None
        for dir_path in log_dirs:
            try:
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path, exist_ok=True)
                if os.access(dir_path, os.W_OK):
                    log_dir = dir_path
                    break
            except Exception:
                continue
        
        if not log_dir:
            safe_print("[!] 无法创建日志目录，使用当前目录")
            log_dir = os.getcwd()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"kugou_launcher_{timestamp}.log"
        LOG_FILE = os.path.join(log_dir, log_filename)
        
        with open(LOG_FILE, 'a', encoding='utf-8', errors='replace') as f:
            f.write("=" * 60 + "\n")
            f.write(f"酷狗音乐拦截启动器启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Python版本: {sys.version}\n")
            f.write(f"操作系统: {sys.platform}\n")
            f.write("=" * 60 + "\n")
        
        safe_print(f"[√] 日志系统已初始化，日志文件: {LOG_FILE}")
        return True
    except Exception as e:
        safe_print(f"[!] 日志初始化失败: {e}")
        return False


def log_message(message: str, level: str = "INFO") -> None:
    safe_log(message, level)


def add_to_startup() -> bool:
    """添加到开机自动启动（开机启动时使用--autostart参数）"""
    try:
        exe_path = None
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            exe_path = os.path.abspath(sys.argv[0])
        
        if not exe_path or not os.path.exists(exe_path):
            safe_print("[!] 无法确定可执行文件路径")
            return False
        
        # 添加--autostart参数，开机启动时不显示菜单
        startup_cmd = f'"{exe_path}" --autostart'
        
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "KuGouInterceptor", 0, winreg.REG_SZ, startup_cmd)
        winreg.CloseKey(key)
        
        safe_print(f"[√] 已添加到开机自动启动: {startup_cmd}")
        log_message(f"已添加到开机自动启动: {startup_cmd}")
        return True
    except Exception as e:
        safe_print(f"[!] 添加到开机启动失败: {e}")
        log_message(f"添加到开机启动失败: {e}", "ERROR")
        return False


def remove_from_startup() -> bool:
    """从开机自动启动中移除"""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, "KuGouInterceptor")
            safe_print("[√] 已从开机自动启动中移除")
            log_message("已从开机自动启动中移除")
        except WindowsError:
            safe_print("[*] 开机启动项不存在")
        winreg.CloseKey(key)
        return True
    except Exception as e:
        safe_print(f"[!] 移除开机启动失败: {e}")
        log_message(f"移除开机启动失败: {e}", "ERROR")
        return False


def check_startup_status() -> bool:
    """检查开机启动状态"""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        try:
            value, _ = winreg.QueryValueEx(key, "KuGouInterceptor")
            winreg.CloseKey(key)
            safe_print(f"[√] 开机启动已启用: {value}")
            return True
        except WindowsError:
            winreg.CloseKey(key)
            safe_print("[*] 开机启动未启用")
            return False
    except Exception as e:
        safe_print(f"[!] 检查开机启动状态失败: {e}")
        return False


def find_kugou_path() -> Optional[str]:
    paths = []
    possible_exe_names = [
        "KuGou.exe", "kugou.exe", "KGMusic.exe", "kgmusic.exe",
        "KuGou7.exe", "kugou7.exe", "KuGou8.exe", "kugou8.exe",
        "KuGou9.exe", "kugou9.exe", "KuGou10.exe", "kugou10.exe",
        "酷狗音乐.exe", "酷狗.exe"
    ]
    possible_subdirs = [
        "KuGou\\KGMusic", "KuGou", "KGMusic",
        "KuGou7\\KGMusic", "KuGou8\\KGMusic", "KuGou9\\KGMusic",
        "KuGou10\\KGMusic", "酷狗音乐", "酷狗",
        "Tencent\\KuGou", "Tencent\\酷狗音乐"
    ]
    
    try:
        key_paths = [
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\KuGou.exe",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\KuGou.exe",
        ]
        
        for key_path in key_paths:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                    if "App Paths" in key_path:
                        try:
                            app_path = winreg.QueryValueEx(key, "")[0]
                            if app_path and safe_file_exists(app_path):
                                paths.append(app_path)
                        except Exception:
                            pass
                    else:
                        i = 0
                        while True:
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    try:
                                        display_name = winreg.QueryValueEx(subkey, "DisplayName")[0] or ""
                                        display_name_lower = display_name.lower()
                                        if "酷狗" in display_name or "kugou" in display_name_lower or "kgmusic" in display_name_lower:
                                            try:
                                                install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                                if install_location:
                                                    for exe_name in possible_exe_names:
                                                        kugou_exe = safe_path_join(install_location, exe_name)
                                                        if kugou_exe and safe_file_exists(kugou_exe):
                                                            paths.append(kugou_exe)
                                                            break
                                            except Exception:
                                                pass
                                    except Exception:
                                        pass
                                i += 1
                            except WindowsError:
                                break
            except Exception:
                continue
    except Exception:
        pass
    
    try:
        drives = []
        for drive_letter in ['C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']:
            try:
                drive_path = f"{drive_letter}:\\"
                if safe_dir_exists(drive_path):
                    drives.append(drive_letter)
            except Exception:
                continue
        
        for drive in drives:
            for arch in ['Program Files (x86)', 'Program Files', 'ProgramData']:
                arch_path = safe_path_join(f"{drive}:\\", arch)
                if not arch_path or not safe_dir_exists(arch_path):
                    continue
                for subdir in possible_subdirs:
                    full_subdir = safe_path_join(arch_path, subdir)
                    if not full_subdir or not safe_dir_exists(full_subdir):
                        continue
                    for exe_name in possible_exe_names:
                        path = safe_path_join(full_subdir, exe_name)
                        if path and safe_file_exists(path) and path not in paths:
                            paths.append(path)
    except Exception:
        pass
    
    try:
        user_profile = os.path.expanduser("~")
        user_dirs = [
            safe_path_join(user_profile, "AppData", "Local", "KuGou"),
            safe_path_join(user_profile, "AppData", "Local", "KGMusic"),
            safe_path_join(user_profile, "AppData", "Roaming", "KuGou"),
            safe_path_join(user_profile, "AppData", "Roaming", "KGMusic"),
            safe_path_join(user_profile, "Desktop"),
        ]
        
        for user_dir in user_dirs:
            if not user_dir or not safe_dir_exists(user_dir):
                continue
            for exe_name in possible_exe_names:
                exe_path = safe_path_join(user_dir, exe_name)
                if exe_path and safe_file_exists(exe_path) and exe_path not in paths:
                    paths.append(exe_path)
    except Exception:
        pass
    
    if paths:
        log_message(f"找到 {len(paths)} 个可能的酷狗路径，选择第一个: {paths[0]}")
        return paths[0]
    return None


def get_project_root() -> str:
    try:
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.getcwd()


def get_bundle_resource_dir() -> str:
    try:
        if getattr(sys, "frozen", False):
            return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.getcwd()


def get_runtime_resource_dir() -> str:
    candidates = [
        os.environ.get("LOCALAPPDATA"),
        os.environ.get("TEMP"),
        get_project_root(),
    ]
    for root in candidates:
        if not root:
            continue
        try:
            runtime_dir = os.path.join(root, RUNTIME_DIR_NAME)
            os.makedirs(runtime_dir, exist_ok=True)
            return runtime_dir
        except Exception:
            continue
    return get_project_root()


def stage_runtime_resource(source_path: Optional[str], relative_path: str) -> Optional[str]:
    if not source_path or not safe_file_exists(source_path):
        return source_path
    try:
        runtime_dir = get_runtime_resource_dir()
        target_path = safe_path_join(runtime_dir, relative_path)
        if not target_path:
            return source_path
        target_dir = os.path.dirname(target_path)
        if target_dir:
            safe_makedirs(target_dir, exist_ok=True)
        should_copy = not safe_file_exists(target_path)
        if not should_copy:
            try:
                should_copy = (
                    os.path.getsize(target_path) != os.path.getsize(source_path) or
                    int(os.path.getmtime(target_path)) != int(os.path.getmtime(source_path))
                )
            except Exception:
                should_copy = True
        if should_copy:
            shutil.copy2(source_path, target_path)
        return target_path
    except Exception as e:
        log_message(f"复制运行时资源失败: {source_path} -> {relative_path}, {e}", "WARNING")
        return source_path


def prepare_runtime_assets(project_dir: str, bundle_dir: str) -> dict:
    def first_existing(paths) -> Optional[str]:
        for path in paths:
            if path and safe_file_exists(path):
                return path
        return None

    assets = {
        "runtime_dir": project_dir,
        "mitmdump_path": first_existing([
            safe_path_join(bundle_dir, "mitmdump.exe"),
            safe_path_join(project_dir, "mitmdump.exe"),
        ]),
        "filter_script": first_existing([
            safe_path_join(bundle_dir, "kugou_filter.py"),
            safe_path_join(project_dir, "kugou_filter.py"),
        ]),
        "ssl_bypass_js": first_existing([
            safe_path_join(bundle_dir, "kugou_ssl_bypass.js"),
            safe_path_join(project_dir, "kugou_ssl_bypass.js"),
        ]),
        "kugou_config": first_existing([
            safe_path_join(bundle_dir, "kugou_config.py"),
            safe_path_join(project_dir, "kugou_config.py"),
        ]),
        "frida_path": first_existing([
            safe_path_join(bundle_dir, "frida.exe"),
            safe_path_join(project_dir, "frida.exe"),
        ]),
    }
    if not getattr(sys, "frozen", False):
        return assets
    runtime_dir = get_runtime_resource_dir()
    assets["runtime_dir"] = runtime_dir
    assets["mitmdump_path"] = stage_runtime_resource(assets["mitmdump_path"], "mitmdump.exe")
    assets["filter_script"] = stage_runtime_resource(assets["filter_script"], "kugou_filter.py")
    assets["ssl_bypass_js"] = stage_runtime_resource(assets["ssl_bypass_js"], "kugou_ssl_bypass.js")
    assets["kugou_config"] = stage_runtime_resource(assets["kugou_config"], "kugou_config.py")
    assets["frida_path"] = stage_runtime_resource(assets["frida_path"], "frida.exe")
    for filename in ["singer_whitelist.txt", "song_whitelist.txt"]:
        source_path = first_existing([
            safe_path_join(bundle_dir, "config", filename),
            safe_path_join(project_dir, "config", filename),
        ])
        stage_runtime_resource(source_path, os.path.join("config", filename))
    return assets


def get_internal_helper_executable() -> Optional[str]:
    try:
        if getattr(sys, "frozen", False) and getattr(sys, "executable", None):
            if safe_file_exists(sys.executable):
                return sys.executable
    except Exception:
        pass
    return None


def is_internal_helper_mode(path: Optional[str]) -> bool:
    try:
        internal_exe = get_internal_helper_executable()
        if not internal_exe or not path:
            return False
        return os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.path.abspath(internal_exe))
    except Exception:
        return False


def run_internal_mitmdump_mode() -> None:
    from mitmproxy.tools.main import mitmdump

    sys.argv = [sys.argv[0]] + sys.argv[2:]
    mitmdump()


def run_internal_frida_mode() -> None:
    from frida_tools.repl import main as frida_main

    sys.argv = [sys.argv[0]] + sys.argv[2:]
    result = frida_main()
    if isinstance(result, int):
        sys.exit(result)


def handle_internal_modes() -> bool:
    try:
        if len(sys.argv) > 1 and sys.argv[1] == INTERNAL_MITMDUMP_FLAG:
            run_internal_mitmdump_mode()
            return True
        if len(sys.argv) > 1 and sys.argv[1] == INTERNAL_FRIDA_FLAG:
            run_internal_frida_mode()
            return True
    except Exception:
        traceback.print_exc()
        sys.exit(1)
    return False


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin() -> None:
    try:
        if not is_admin():
            try:
                ctypes.windll.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
                sys.exit(0)
            except Exception as e:
                safe_print(f"[!] 请求管理员权限失败: {e}")
                safe_print("[*] 继续以当前权限运行...")
    except Exception:
        pass


def find_kugou_pid() -> Optional[int]:
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = proc.info['name']
                if name and name.lower() in ['kugou.exe', 'kugou']:
                    return proc.info['pid']
            except Exception:
                continue
    except Exception:
        pass
    return None


def find_kugou_main_process():
    """
    检测酷狗音乐主进程，返回主进程完整信息/None
    核心区分逻辑：主进程是酷狗进程树的根进程，子进程的父进程均为主进程
    """
    kugou_process_list = []
    # 1. 遍历系统所有进程，筛选出酷狗的全部进程
    for proc in psutil.process_iter(['pid', 'name', 'ppid', 'memory_info', 'exe', 'status']):
        try:
            # 匹配酷狗进程映像名，不区分大小写
            if proc.info['name'].lower() == 'kugou.exe':
                kugou_process_list.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # 忽略无权限、已退出的进程
            continue

    if not kugou_process_list:
        return None

    # 2. 定位主进程：父进程不属于酷狗进程集合的，就是根主进程
    all_kugou_pids = {proc['pid'] for proc in kugou_process_list}
    main_process = None
    for proc in kugou_process_list:
        if proc['ppid'] not in all_kugou_pids:
            main_process = proc
            break

    # 兜底逻辑：父子关系获取失败时，返回带主窗口的UI进程
    if not main_process and HAS_WIN32:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() == 'kugou.exe':
                    def callback(hwnd, extra):
                        if win32gui.IsWindowVisible(hwnd):
                            title = win32gui.GetWindowText(hwnd)
                            if '酷狗音乐' in title:
                                extra.append(proc.info)
                                return False
                        return True
                    found = []
                    win32gui.EnumWindows(callback, found)
                    if found:
                        main_process = found[0]
                        break
            except:
                continue

    return main_process


def _local_proxy_port_open(port: int = DEFAULT_MITM_PORT, timeout: float = 0.75) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def install_mitmproxy_ca_certificate():
    """自动安装mitmproxy CA证书到系统受信任的根证书颁发机构"""
    try:
        safe_print("[*] 开始检查mitmproxy CA证书...")
        # 获取mitmproxy CA证书路径
        ca_cert_path = os.path.join(os.path.expanduser("~"), ".mitmproxy", "mitmproxy-ca-cert.pem")
        
        if not os.path.exists(ca_cert_path):
            safe_print(f"[!] mitmproxy CA证书不存在: {ca_cert_path}")
            safe_print("[!] 请先运行一次mitmproxy以生成证书")
            log_message(f"mitmproxy CA证书不存在: {ca_cert_path}", "WARNING")
            log_message("请先运行一次mitmproxy以生成证书", "WARNING")
            return False
        
        # 转换为DER格式（Windows需要）
        der_cert_path = os.path.join(os.path.expanduser("~"), ".mitmproxy", "mitmproxy-ca-cert.crt")
        
        # 检查是否已安装
        cert_installed = False
        try:
            import subprocess
            result = subprocess.run(
                ["certutil", "-store", "root", "mitmproxy"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if "mitmproxy" in result.stdout.lower():
                cert_installed = True
        except Exception:
            pass
        
        if cert_installed:
            safe_print("[√] mitmproxy CA证书已安装，无需重复安装")
            log_message("mitmproxy CA证书已安装，无需重复安装")
            return True
        
        # 如果DER证书不存在，使用OpenSSL转换
        if not os.path.exists(der_cert_path):
            try:
                # 尝试使用cryptography库转换
                from cryptography import x509
                from cryptography.hazmat.primitives import serialization
                
                with open(ca_cert_path, "rb") as f:
                    cert = x509.load_pem_x509_certificate(f.read())
                
                der_data = cert.public_bytes(encoding=serialization.Encoding.DER)
                
                with open(der_cert_path, "wb") as f:
                    f.write(der_data)
                
                safe_print("[√] 已将CA证书转换为DER格式")
                log_message("已将CA证书转换为DER格式")
            except Exception as e:
                safe_print(f"[!] 转换证书格式失败: {e}")
                log_message(f"转换证书格式失败: {e}", "WARNING")
                # 尝试直接使用PEM格式
                der_cert_path = ca_cert_path
        
        # 使用certutil安装证书
        try:
            import subprocess
            safe_print("[*] 正在安装CA证书...")
            result = subprocess.run(
                ["certutil", "-addstore", "root", der_cert_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                safe_print("[√] mitmproxy CA证书安装成功")
                log_message("mitmproxy CA证书安装成功")
                return True
            else:
                safe_print(f"[!] CA证书安装失败: {result.stderr}")
                log_message(f"CA证书安装失败: {result.stderr}", "ERROR")
                return False
        except Exception as e:
            safe_print(f"[!] 安装CA证书时出错: {e}")
            log_message(f"安装CA证书时出错: {e}", "ERROR")
            safe_print("[!] 请手动安装mitmproxy CA证书")
            log_message("请手动安装mitmproxy CA证书", "WARNING")
            return False
            
    except Exception as e:
        safe_print(f"[!] CA证书安装过程出错: {e}")
        log_message(f"CA证书安装过程出错: {e}", "ERROR")
        log_message(traceback.format_exc(), "ERROR")
        return False


def terminate_listeners_on_port(port: int = DEFAULT_MITM_PORT) -> bool:
    seen = set()
    killed = False
    
    try:
        for conn in psutil.net_connections(kind="tcp"):
            try:
                if conn.status != psutil.CONN_LISTEN:
                    continue
                if conn.laddr is None or getattr(conn.laddr, "port", None) != port:
                    continue
                pid = conn.pid
                if not pid or pid in seen:
                    continue
                seen.add(pid)
                
                try:
                    p = psutil.Process(pid)
                    pname = (p.name() or "").lower()
                    safe_print(f"[*] 终止占用端口 {port} 的进程: {pname} (PID: {pid})")
                    log_message(f"终止占用端口 {port} 的进程: {pname} PID={pid}", "WARNING")
                    
                    try:
                        p.terminate()
                        try:
                            p.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            try:
                                p.kill()
                            except Exception:
                                pass
                        killed = True
                    except Exception:
                        pass
                except Exception:
                    pass
            except Exception:
                continue
    except Exception as e:
        log_message(f"枚举端口监听失败: {e}", "ERROR")
    
    return killed


def _cmdline_looks_like_mitmdump(cmdline: list) -> bool:
    if not cmdline:
        return False
    try:
        joined = " ".join(str(a) for a in cmdline).lower()
        return any(
            m in joined
            for m in (
                "mitmdump",
                "mitmproxy.tools.dump",
                "mitmproxy.tools.main",
                "-m mitmproxy",
            )
        )
    except Exception:
        return False


def kill_existing_mitmdump(port: int = DEFAULT_MITM_PORT) -> bool:
    killed = False
    
    try:
        killed = terminate_listeners_on_port(port)
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = proc.info.get('name', '')
                if not name:
                    continue
                
                name_lower = name.lower()
                
                if name_lower == 'mitmdump.exe':
                    try:
                        safe_print(f"[*] 发现旧的 mitmdump 进程 (PID: {proc.info['pid']})，正在终止...")
                        log_message(f"发现旧的 mitmdump 进程 (PID: {proc.info['pid']})，正在终止...", "WARNING")
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            proc.kill()
                        killed = True
                    except Exception:
                        pass
                
                elif name_lower in ("python.exe", "pythonw.exe"):
                    try:
                        cl = proc.cmdline()
                        if _cmdline_looks_like_mitmdump(cl):
                            safe_print(f"[*] 发现 python 托管的 mitmdump (PID: {proc.info['pid']})，正在终止...")
                            log_message(f"终止 python 托管 mitmdump PID={proc.info['pid']}", "WARNING")
                            proc.terminate()
                            try:
                                proc.wait(timeout=3)
                            except psutil.TimeoutExpired:
                                proc.kill()
                            killed = True
                    except Exception:
                        continue
            except Exception:
                continue
        
        if killed:
            safe_print("[√] 旧进程已清理")
            log_message("旧进程已清理")
            time.sleep(1)
    
    except Exception as e:
        safe_print(f"[!] 清理进程时出错: {e}")
        log_message(f"清理进程时出错: {e}", "ERROR")
    
    return killed


def find_command(command_name: str) -> Optional[str]:
    import shutil
    
    log_message(f"正在查找命令: {command_name}")
    paths_to_check = []
    
    try:
        project_root = get_project_root()
        log_message(f"优先检查项目根目录: {project_root}")
        paths_to_check.append(safe_path_join(project_root, command_name + ".exe"))
    except Exception:
        pass
    
    try:
        cwd = os.getcwd()
        log_message(f"检查当前工作目录: {cwd}")
        paths_to_check.append(safe_path_join(cwd, command_name + ".exe"))
    except Exception:
        pass
    
    try:
        if getattr(sys, 'frozen', False):
            try:
                base_path = sys._MEIPASS
                log_message(f"打包模式，临时目录: {base_path}")
                paths_to_check.append(safe_path_join(base_path, command_name + ".exe"))
            except Exception:
                pass
            
            try:
                exe_dir = os.path.dirname(sys.executable)
                paths_to_check.append(safe_path_join(exe_dir, command_name + ".exe"))
            except Exception:
                pass
    except Exception:
        pass
    
    try:
        path = shutil.which(command_name)
        if path:
            paths_to_check.append(path)
    except Exception:
        pass
    
    try:
        python_dir = os.path.dirname(sys.executable)
        scripts_dir = safe_path_join(python_dir, "Scripts")
        if scripts_dir and safe_dir_exists(scripts_dir):
            paths_to_check.append(safe_path_join(scripts_dir, command_name + ".exe"))
            paths_to_check.append(safe_path_join(scripts_dir, command_name + ".cmd"))
    except Exception:
        pass
    
    for cmd_path in paths_to_check:
        try:
            if cmd_path and safe_file_exists(cmd_path) and os.access(cmd_path, os.X_OK):
                log_message(f"找到命令: {cmd_path}")
                return cmd_path
        except Exception:
            continue
    
    log_message(f"未找到命令: {command_name}", "WARNING")
    return None


def is_mitmdump_running(
    filter_script: Optional[str] = None,
    proxy_process: Optional[subprocess.Popen] = None,
    port: int = DEFAULT_MITM_PORT
) -> bool:
    try:
        if proxy_process is not None:
            try:
                if proxy_process.poll() is None:
                    log_message("mitmproxy: 子进程句柄仍存活 (Popen)")
                    return True
            except Exception:
                pass
    except Exception:
        pass
    
    try:
        if _local_proxy_port_open(port):
            log_message(f"mitmproxy: 127.0.0.1:{port} 可连接，判定代理已监听")
            return True
    except Exception:
        pass
    
    script_name = None
    if filter_script:
        try:
            script_name = os.path.basename(filter_script)
        except Exception:
            pass
    
    try:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                n = (proc.info.get("name") or "").lower()
                
                if n == "mitmdump.exe":
                    if filter_script and script_name:
                        try:
                            cmdline = proc.info.get("cmdline") or []
                            if not any(script_name in (arg or "") for arg in cmdline):
                                continue
                        except Exception:
                            pass
                    log_message(f"mitmproxy: 发现 mitmdump.exe PID={proc.pid}")
                    return True
                
                if n in ("python.exe", "pythonw.exe"):
                    try:
                        cmdline = proc.info.get("cmdline")
                        if not _cmdline_looks_like_mitmdump(cmdline):
                            continue
                        if filter_script and script_name:
                            try:
                                flat = [str(x) for x in (cmdline or [])]
                                if not any(script_name in x for x in flat):
                                    continue
                            except Exception:
                                pass
                        log_message(f"mitmproxy: 发现 python 托管 mitmdump PID={proc.pid}")
                        return True
                    except Exception:
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception:
                continue
    except psutil.AccessDenied:
        log_message("检查进程时权限被拒绝", "WARNING")
    except Exception as e:
        log_message(f"检查进程时出错: {e}", "ERROR")
    
    return False


def find_mitmdump() -> Tuple[Optional[str], bool]:
    mitmdump_path = find_command("mitmdump")
    use_python_module = False
    
    if not mitmdump_path:
        log_message("找不到独立的 mitmdump.exe，尝试通过 Python 模块启动", "WARNING")
        
        python_path = None
        for cmd in ["python", "pythonw", "py"]:
            path = find_command(cmd)
            if path:
                python_path = path
                break
        
        if not python_path and hasattr(sys, 'executable') and sys.executable:
            python_path = sys.executable
            log_message(f"使用当前 Python 解释器: {python_path}")
        
        if python_path:
            try:
                test_cmd = [python_path, "-c", "import mitmproxy.tools.dump; print('OK')"]
                result = subprocess.run(
                    test_cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    errors='replace'
                )
                if result.returncode == 0:
                    mitmdump_path = python_path
                    use_python_module = True
                    log_message("通过 Python 模块启动 mitmdump")
            except Exception as e:
                log_message(f"检查 mitmproxy 模块失败: {e}", "ERROR")
    
    return mitmdump_path, use_python_module


def safe_process_terminate(process: Optional[subprocess.Popen]) -> None:
    if not process:
        return
    
    try:
        if process.poll() is None:
            try:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        process.kill()
                        process.wait(timeout=3)
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception:
        pass


def safe_file_exists(filepath: str) -> bool:
    try:
        return os.path.exists(filepath)
    except Exception:
        return False


def safe_dir_exists(dirpath: str) -> bool:
    try:
        return os.path.isdir(dirpath)
    except Exception:
        return False


def safe_path_join(*paths) -> Optional[str]:
    try:
        return os.path.join(*paths)
    except Exception:
        return None


def safe_makedirs(path: str, exist_ok: bool = True) -> bool:
    try:
        os.makedirs(path, exist_ok=exist_ok)
        return True
    except Exception:
        return False


def get_system_info() -> dict:
    info = {}
    try:
        info['platform'] = sys.platform
        info['python_version'] = sys.version
        info['python_implementation'] = sys.implementation.name if hasattr(sys, 'implementation') else 'unknown'
        info['is_frozen'] = getattr(sys, 'frozen', False)
    except Exception as e:
        safe_log(f"获取系统信息失败: {e}", "WARNING")
    return info


def is_process_running(pid: int) -> bool:
    try:
        return psutil.pid_exists(pid)
    except Exception:
        return False


def test_mitmdump_execution(mitmdump_path: str, use_python_module: bool = False) -> Tuple[bool, str]:
    try:
        if use_python_module:
            test_cmd = [mitmdump_path, "-c", "import mitmproxy.tools.dump; print('OK')"]
            test_desc = "Python模块测试"
        else:
            test_cmd = [mitmdump_path, "--version"]
            test_desc = "独立exe测试"
        
        log_message(f"执行{test_desc}: {' '.join(test_cmd)}")
        
        result = subprocess.run(
            test_cmd,
            capture_output=True,
            text=True,
            timeout=30,
            errors='replace'
        )
        
        output = (result.stdout or "") + (result.stderr or "")
        log_message(f"{test_desc}输出: {output[:500]}")
        
        if result.returncode == 0:
            return True, f"{test_desc}成功"
        else:
            return False, f"{test_desc}失败，返回码: {result.returncode}, 输出: {output[:200]}"
            
    except subprocess.TimeoutExpired:
        return False, f"{test_desc}超时"
    except Exception as e:
        return False, f"{test_desc}异常: {e}"


def diagnose_mitmproxy_installation() -> dict:
    diagnosis = {
        'python_available': False,
        'mitmproxy_module': False,
        'mitmdump_exe': False,
        'module_version': None,
        'possible_paths': [],
        'errors': []
    }
    
    try:
        diagnosis['python_available'] = True
        
        try:
            import mitmproxy
            diagnosis['mitmproxy_module'] = True
            try:
                diagnosis['module_version'] = getattr(mitmproxy, '__version__', 'unknown')
            except Exception:
                pass
        except ImportError as e:
            diagnosis['errors'].append(f"mitmproxy模块导入失败: {e}")
        except Exception as e:
            diagnosis['errors'].append(f"检查mitmproxy模块时出错: {e}")
        
        mitmdump_exe_names = ['mitmdump.exe', 'mitmdump']
        for exe_name in mitmdump_exe_names:
            path = find_command(exe_name)
            if path:
                diagnosis['possible_paths'].append(path)
                diagnosis['mitmdump_exe'] = True
                break
                
    except Exception as e:
        diagnosis['errors'].append(f"诊断过程出错: {e}")
    
    return diagnosis


def find_mitmdump_enhanced() -> Tuple[Optional[str], bool, list]:
    possible_methods = []
    
    diagnosis = diagnose_mitmproxy_installation()
    log_message(f"Mitmproxy诊断结果: {diagnosis}")
    
    for path in diagnosis['possible_paths']:
        success, message = test_mitmdump_execution(path, use_python_module=False)
        if success:
            possible_methods.append((path, False, message))
            log_message(f"找到可用的mitmdump独立exe: {path}")
        else:
            log_message(f"mitmdump独立exe测试失败: {message}", "WARNING")
    
    if diagnosis['mitmproxy_module']:
        for python_cmd in ["python", "pythonw", "py", sys.executable]:
            if python_cmd and python_cmd != "None":
                python_path = find_command(python_cmd)
                if python_path:
                    success, message = test_mitmdump_execution(python_path, use_python_module=True)
                    if success:
                        possible_methods.append((python_path, True, message))
                        log_message(f"找到可用的Python模块方式: {python_path}")
                        break
    
    log_message(f"共找到 {len(possible_methods)} 种mitmdump启动方式")
    return possible_methods[0] if possible_methods else (None, False, "未找到可用的mitmdump")


def launch_mitmdump_with_fallback(
    filter_script: str,
    project_dir: str,
    max_attempts: int = 3,
    preferred_mitmdump_path: Optional[str] = None,
) -> Tuple[Optional[subprocess.Popen], Optional[str], bool]:
    
    possible_methods = []
    
    try:
        internal_exe = get_internal_helper_executable()
        if internal_exe:
            possible_methods.append((internal_exe, False, "内置mitmdump模式"))

        if preferred_mitmdump_path and safe_file_exists(preferred_mitmdump_path):
            success, message = test_mitmdump_execution(preferred_mitmdump_path, use_python_module=False)
            if success:
                possible_methods.append((preferred_mitmdump_path, False, "持久化运行时目录"))
            else:
                log_message(f"持久化运行时 mitmdump 测试失败: {message}", "WARNING")
        enhanced_result = find_mitmdump_enhanced()
        if enhanced_result[0]:
            possible_methods.append(enhanced_result)
        
        basic_path, basic_use_module = find_mitmdump()
        if basic_path and not any(m[0] == basic_path and m[1] == basic_use_module for m in possible_methods):
            possible_methods.append((basic_path, basic_use_module, "基础查找方式"))
    
    except Exception as e:
        log_message(f"获取mitmdump启动方式时出错: {e}", "ERROR")
    
    if not possible_methods:
        safe_print("[!] 未找到任何可用的mitmdump启动方式")
        log_message("未找到任何可用的mitmdump启动方式", "ERROR")
        return None, None, False
    
    log_message(f"尝试使用 {len(possible_methods)} 种方式启动mitmdump")
    
    for attempt in range(max_attempts):
        for method_idx, (mitmdump_path, use_python_module, method_desc) in enumerate(possible_methods):
            safe_print(f"[*] 尝试方式 {method_idx + 1}/{len(possible_methods)} (尝试 {attempt + 1}/{max_attempts}): {method_desc}")
            log_message(f"启动mitmdump - 方式{method_idx + 1}, 尝试{attempt + 1}: {mitmdump_path}")
            
            try:
                kill_existing_mitmdump()
                time.sleep(2)
                
                if is_internal_helper_mode(mitmdump_path):
                    cmd = [
                        mitmdump_path,
                        INTERNAL_MITMDUMP_FLAG,
                        "-s", filter_script,
                        "--ssl-insecure",
                        "--set", "block_global=false"
                    ]
                elif use_python_module:
                    cmd = [
                        mitmdump_path, "-m", "mitmproxy.tools.dump",
                        "-s", filter_script,
                        "--ssl-insecure",
                        "--set", "block_global=false"
                    ]
                else:
                    cmd = [
                        mitmdump_path,
                        "-s", filter_script,
                        "--ssl-insecure",
                        "--set", "block_global=false"
                    ]
                
                log_message(f"执行命令: {' '.join(cmd)}")
                
                proxy_process = subprocess.Popen(
                    cmd,
                    cwd=project_dir,
                    shell=False
                )
                
                wait_time = min(10 + attempt * 5, 30)
                safe_print(f"[*] 已启动 mitmdump ({wait_time}秒)...")
                time.sleep(wait_time)
                
                if is_mitmdump_running(filter_script=filter_script, proxy_process=proxy_process):
                    safe_print(f"[√] Mitmdump启动成功 (方式{method_idx + 1})")
                    log_message(f"Mitmdump启动成功，使用方式: {method_desc}")
                    return proxy_process, mitmdump_path, use_python_module
                else:
                    safe_print(f"[!] Mitmdump启动验证失败 (方式{method_idx + 1})")
                    log_message(f"Mitmdump启动验证失败", "WARNING")
                    
                    if proxy_process.poll() is not None:
                        log_message(f"Mitmdump已退出，返回码: {proxy_process.returncode}", "ERROR")
                    
                    safe_process_terminate(proxy_process)
                    time.sleep(2)
                    
            except Exception as e:
                safe_print(f"[!] 启动mitmdump时出错: {e}")
                log_message(f"启动mitmdump异常: {e}", "ERROR")
                log_message(traceback.format_exc(), "ERROR")
    
    safe_print("[!] 所有启动方式均失败")
    log_message("所有mitmdump启动方式均失败", "ERROR")
    return None, None, False


def cleanup_resources(
    proxy_process: Optional[subprocess.Popen] = None,
    frida_process: Optional[subprocess.Popen] = None,
    cleanup_mitmdump: bool = True,
    cleanup_frida: bool = True,
    cleanup_kugou: bool = False
) -> None:
    log_message("开始清理资源...")
    
    try:
        if proxy_process:
            safe_print("[*] 清理代理进程...")
            safe_process_terminate(proxy_process)
    except Exception as e:
        log_message(f"清理代理进程时出错: {e}", "WARNING")

    try:
        if cleanup_frida and frida_process:
            safe_print("[*] 清理 SSL 绕过进程...")
            safe_process_terminate(frida_process)
    except Exception as e:
        log_message(f"清理 SSL 绕过进程时出错: {e}", "WARNING")
    
    try:
        if cleanup_mitmdump:
            safe_print("[*] 清理所有 mitmdump 进程...")
            kill_existing_mitmdump()
    except Exception as e:
        log_message(f"清理 mitmdump 时出错: {e}", "WARNING")
    
    try:
        if cleanup_kugou:
            kugou_pid = find_kugou_pid()
            if kugou_pid:
                safe_print(f"[*] 清理酷狗进程 (PID: {kugou_pid})...")
                try:
                    proc = psutil.Process(kugou_pid)
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        proc.kill()
                except Exception as e:
                    log_message(f"清理酷狗进程时出错: {e}", "WARNING")
    except Exception as e:
        log_message(f"清理酷狗进程时出错: {e}", "WARNING")
    
    log_message("资源清理完成")


class KugouProcessMonitor:
    """酷狗进程监控器 - 实时检测酷狗进程"""
    
    def __init__(self, filter_script: str, ssl_bypass_js: str, project_dir: str):
        self.filter_script = filter_script
        self.ssl_bypass_js = ssl_bypass_js
        self.project_dir = project_dir
        self.running = False
        self.monitor_thread = None
        self.kugou_detected = False
        self.kugou_running = False
    
    def start(self):
        """启动监控"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        safe_print("[√] 酷狗进程监控已启动")
        safe_print("[!] 重要提示：请在酷狗音乐设置中配置代理: 127.0.0.1:8080")
        log_message("酷狗进程监控已启动")
    
    def stop(self):
        """停止监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        safe_print("[*] 酷狗进程监控已停止")
        log_message("酷狗进程监控已停止")
    
    def _monitor_loop(self):
        """监控主循环"""
        while self.running:
            try:
                self._check_kugou_processes()
                time.sleep(PROCESS_MONITOR_INTERVAL)
            except Exception as e:
                safe_print(f"[!] 进程监控异常: {e}")
                log_message(f"进程监控异常: {e}", "ERROR")
                log_message(traceback.format_exc(), "ERROR")
    
    def _check_kugou_processes(self):
        """检查酷狗进程 - 使用主进程检测逻辑"""
        main_process = find_kugou_main_process()
        
        if main_process and not self.kugou_running:
            self.kugou_running = True
            if not self.kugou_detected:
                self.kugou_detected = True
                safe_print("[+] 检测到酷狗音乐主进程")
                safe_print(f"    进程PID: {main_process['pid']}")
                safe_print(f"    运行状态: {main_process['status']}")
                log_message(f"检测到酷狗音乐主进程 PID={main_process['pid']}")
        elif not main_process and self.kugou_running:
            self.kugou_running = False
            safe_print("[-] 酷狗音乐主进程已退出")
            log_message("酷狗音乐主进程已退出")


def monitor_processes_enhanced(
    proxy_process: Optional[subprocess.Popen],
    filter_script: str,
    ssl_bypass_js: str,
    project_dir: str,
    kugou_monitor: KugouProcessMonitor,
) -> Optional[subprocess.Popen]:
    """增强的进程监控"""
    log_message("增强进程监控已启动")
    
    if is_mitmdump_running(filter_script=filter_script, proxy_process=proxy_process):
        log_message("初始状态: mitmdump 正在运行")
    else:
        log_message("初始状态: mitmdump 未运行", "WARNING")
    
    consecutive_failures = 0
    total_restarts = 0
    last_health_check = time.time()
    
    while True:
        try:
            current_time = time.time()

            if is_mitmdump_running(
                filter_script=filter_script, proxy_process=proxy_process
            ):
                consecutive_failures = 0
                
                if current_time - last_health_check > HEALTH_CHECK_INTERVAL:
                    log_message("健康检查: 代理进程运行正常")
                    last_health_check = current_time
                
                time.sleep(PROCESS_MONITOR_INTERVAL)
                continue
            
            consecutive_failures += 1
            total_restarts += 1
            safe_print(f"[*] 检测到代理进程异常 (连续{consecutive_failures}次，总重启次数:{total_restarts})，正在重启...")
            log_message(
                f"检测到代理异常（子进程已退出且本机代理端口无响应），连续{consecutive_failures}次，正在重启...",
                "WARNING",
            )
            
            if consecutive_failures > MAX_RETRY_COUNT:
                safe_print(f"[!] 重启失败次数过多({MAX_RETRY_COUNT}次)，采用渐进式等待策略...")
                wait_time = min(RETRY_DELAY * (2 ** (consecutive_failures - MAX_RETRY_COUNT)), 60)
                log_message(f"重启失败次数过多，等待{wait_time}秒（渐进式退避）", "WARNING")
                time.sleep(wait_time)
                
                if consecutive_failures > MAX_CONSECUTIVE_FAILURES:
                    safe_print(f"[!] 连续失败次数达到上限({MAX_CONSECUTIVE_FAILURES})，重置失败计数...")
                    log_message("连续失败次数达到上限，重置失败计数", "WARNING")
                    consecutive_failures = 0
                continue
            
            safe_print("[*] 清理旧进程...")
            kill_existing_mitmdump()
            
            safe_print("[*] 尝试使用增强方式重启mitmdump...")
            new_proxy, new_path, new_use_module = launch_mitmdump_with_fallback(
                filter_script, 
                project_dir,
                max_attempts=2,
                preferred_mitmdump_path=safe_path_join(project_dir, "mitmdump.exe")
            )
            
            if new_proxy:
                proxy_process = new_proxy
                safe_print("[√] 代理已重启")
                log_message("代理已重启")
                
                if is_mitmdump_running(
                    filter_script=filter_script, proxy_process=proxy_process
                ):
                    log_message("验证: mitmdump 进程已成功启动")
                    consecutive_failures = 0
                    last_health_check = current_time
                else:
                    log_message("警告: mitmdump 进程可能未成功启动", "WARNING")
                    if proxy_process and proxy_process.poll() is not None:
                        log_message(f"mitmdump 已退出，返回码: {proxy_process.returncode}", "ERROR")
            else:
                safe_print("[!] 代理重启失败")
                log_message("代理重启失败", "ERROR")
                proxy_process = None
            
            time.sleep(PROCESS_MONITOR_INTERVAL)
            
        except KeyboardInterrupt:
            log_message("进程监控收到退出信号")
            break
        except Exception as e:
            safe_print(f"[!] 监控过程出错: {e}")
            log_message(f"监控过程出错: {e}", "ERROR")
            log_message(traceback.format_exc(), "ERROR")
            time.sleep(PROCESS_MONITOR_INTERVAL)
    
    return proxy_process


def main():
    if handle_internal_modes():
        return

    run_as_admin()
    
    init_logger()
    log_message("酷狗音乐拦截启动器 (调错版) 启动")
    
    # 检测是否是开机自动启动（--autostart参数）
    is_autostart = "--autostart" in sys.argv
    
    if is_autostart:
        # 开机自动启动模式：直接启动拦截器，不显示菜单
        log_message("开机自动启动模式")
    else:
        safe_print("=" * 60)
        safe_print("  酷狗音乐拦截启动器 (调错版)")
        safe_print("  - 窗口可见，完整输出")
        safe_print("  - 开机自动启动")
        safe_print("  - 酷狗进程实时监控")
        safe_print("=" * 60)
        
        print("\n[功能菜单]")
        print("1. 启动拦截器（默认）")
        print("2. 启用开机自动启动")
        print("3. 禁用开机自动启动")
        print("4. 检查开机启动状态")
        
        choice = "1"
        try:
            print("\n请选择功能 (默认1, 5秒后自动选择1): ", end="", flush=True)
            import select
            if sys.stdin in select.select([sys.stdin], [], [], 5)[0]:
                choice = input().strip() or "1"
            else:
                print("1 (自动)")
        except:
            pass
        
        if choice == "2":
            add_to_startup()
            print("\n按任意键退出...")
            input()
            return
        elif choice == "3":
            remove_from_startup()
            print("\n按任意键退出...")
            input()
            return
        elif choice == "4":
            check_startup_status()
            print("\n按任意键退出...")
            input()
            return
    
    system_info = get_system_info()
    log_message(f"系统信息: {system_info}")
    
    proxy_process = None
    frida_process = None
    kugou_monitor = None
    
    try:
        project_dir = get_project_root()
        bundle_dir = get_bundle_resource_dir()
        runtime_assets = prepare_runtime_assets(project_dir, bundle_dir)
        proxy_cwd = runtime_assets.get("runtime_dir") or project_dir
        
        try:
            os.chdir(project_dir)
            safe_print(f"[√] 工作目录: {project_dir}")
            log_message(f"工作目录: {project_dir}")
        except Exception as e:
            safe_print(f"[!] 切换工作目录失败: {e}")
            log_message(f"切换工作目录失败: {e}", "WARNING")
        
        safe_print("\n[1/4] 初始化环境...")
        log_message("开始初始化环境")
        
        filter_script = runtime_assets.get("filter_script")
        ssl_bypass_js = runtime_assets.get("ssl_bypass_js")
        
        if not filter_script:
            safe_print("[!] 过滤器脚本不存在")
            log_message("过滤器脚本不存在", "ERROR")
            time.sleep(10)
            return
        
        safe_print("[√] 环境初始化完成")
        log_message("环境初始化完成")
        
        safe_print(f"\n[2/4] 启动代理...")
        safe_print(f"[*] 脚本: {filter_script}")
        log_message(f"准备启动代理，脚本: {filter_script}")
        
        safe_print("[*] 检查并清理旧代理进程...")
        log_message("检查并清理旧代理进程")
        kill_existing_mitmdump()
        
        install_mitmproxy_ca_certificate()
        
        safe_print("[*] 诊断mitmproxy安装状态...")
        proxy_process, mitmdump_path, use_python_module = launch_mitmdump_with_fallback(
            filter_script, 
            proxy_cwd,
            max_attempts=3,
            preferred_mitmdump_path=runtime_assets.get("mitmdump_path")
        )
        
        if not proxy_process:
            safe_print("[!] Mitmdump启动失败！")
            safe_print("[!] 请检查mitmproxy安装: pip install mitmproxy")
            safe_print("[!] 详细信息请查看日志文件")
            log_message("Mitmdump启动失败，程序终止", "ERROR")
            time.sleep(15)
            return
        
        safe_print(f"[*] mitmdump路径: {mitmdump_path}")
        safe_print(f"[*] 启动方式: {'Python模块' if use_python_module else '独立exe'}")
        
        if is_mitmdump_running(
            filter_script=filter_script, proxy_process=proxy_process
        ):
            safe_print("[√] 验证: mitmdump 进程已成功启动")
            log_message("验证: mitmdump 进程已成功启动")
        else:
            safe_print("[!] 警告: mitmdump 进程可能未成功启动")
            log_message("警告: mitmdump 进程可能未成功启动", "WARNING")
            if proxy_process and proxy_process.poll() is not None:
                log_message(f"mitmdump 已退出，返回码: {proxy_process.returncode}", "ERROR")
        
        safe_print(f"\n[3/4] 启动酷狗进程监控...")
        kugou_monitor = KugouProcessMonitor(filter_script, ssl_bypass_js or "", project_dir)
        kugou_monitor.start()
        
        kugou_path = find_kugou_path()
        safe_print(f"\n[4/4] 检测酷狗音乐...")
        safe_print(f"[*] 酷狗路径: {kugou_path if kugou_path else '未找到'}")
        log_message(f"准备启动酷狗，路径: {kugou_path if kugou_path else '未找到'}")
        
        existing_kugou_main = find_kugou_main_process()
        if existing_kugou_main:
            safe_print(f"[√] 发现正在运行的酷狗主进程 PID={existing_kugou_main['pid']}")
            safe_print(f"[!] 请确保酷狗音乐已配置代理: 127.0.0.1:8080")
        elif kugou_path:
            safe_print("[*] 酷狗未运行，请手动启动酷狗音乐")
            safe_print(f"[*] 或点击这里启动: {kugou_path}")
        else:
            safe_print("[!] 未找到酷狗音乐安装路径")
        
        safe_print("\n" + "=" * 60)
        safe_print("[√] 所有操作完成！")
        safe_print("[*] 酷狗进程监控已启动，将自动检测新进程")
        safe_print("[*] 启动器会自动监控代理进程，如果异常会自动重启")
        safe_print("[*] 按 Ctrl+C 可以退出启动器")
        safe_print("=" * 60)
        log_message("所有操作完成")
        
        try:
            monitor_processes_enhanced(
                proxy_process,
                filter_script,
                ssl_bypass_js or "",
                project_dir,
                kugou_monitor,
            )
        except KeyboardInterrupt:
            safe_print("\n[*] 收到退出信号，正在清理...")
            log_message("收到退出信号，正在清理")
    
    except Exception as e:
        safe_print("\n" + "!" * 60)
        safe_print(f"[!] 发生严重错误: {e}")
        safe_print("!" * 60)
        log_message(f"发生严重错误: {e}", "ERROR")
        log_message(traceback.format_exc(), "ERROR")
        safe_print("\n[*] 等待15秒后退出...")
        time.sleep(15)
    
    safe_print("\n[*] 开始清理资源...")
    if kugou_monitor:
        kugou_monitor.stop()
    cleanup_resources(
        proxy_process,
        frida_process=frida_process,
        cleanup_mitmdump=True,
        cleanup_frida=True,
        cleanup_kugou=False,
    )
    safe_print("\n[*] 退出启动器")
    sys.exit(0)


if __name__ == "__main__":
    main()
