@echo off
chcp 65001 >nul
echo ========================================
echo   酷狗音乐拦截脚本 - 打包脚本
echo ========================================
echo.

echo [1/2] 打包调错版...
pyinstaller --clean build_debug.spec
if %ERRORLEVEL% NEQ 0 (
    echo [!] 调错版打包失败！
    pause
    exit /b 1
)
echo [√] 调错版打包完成
echo.

echo [2/2] 打包发行v2版...
pyinstaller --clean build_v2.spec
if %ERRORLEVEL% NEQ 0 (
    echo [!] 发行v2版打包失败！
    pause
    exit /b 1
)
echo [√] 发行v2版打包完成
echo.

echo ========================================
echo   所有版本打包完成！
echo   输出目录: dist\
echo ========================================
echo.
pause
