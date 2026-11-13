@echo off
rem Anything Copy — 一键启动
rem 双击本文件即可打开；程序数据在 文档\Anything Copy\，配置在 %APPDATA% 对应目录。
cd /d "%~dp0"
start "" "craft-anything.exe" %*
