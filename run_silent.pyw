# -*- coding: utf-8 -*-
"""计划任务静默启动器（.pyw 文件用 pythonw 运行，不产生控制台黑框）

用法:
  pythonw run_silent.pyw <日志文件> <jomoo_toilet.py 的参数...>

示例:
  pythonw run_silent.pyw logs\\foot_off.log foot off

本脚本以 __main__ 方式加载 jomoo_toilet.py，并把它的 print 输出
追加写入指定日志文件。可直接拿 python.exe 运行以便调试。
"""
import os
import runpy
import sys
from datetime import datetime


def main():
    if len(sys.argv) < 3:
        sys.exit("用法: pythonw run_silent.pyw <日志文件> <脚本参数...>")
    log_path = os.path.abspath(sys.argv[1])
    tool = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jomoo_toilet.py")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("===== " + datetime.now().strftime("%Y-%m-%dT%H:%M:%S") + "\n")
        f.flush()
        sys.stdout = f
        sys.stderr = f
        sys.argv = [tool] + sys.argv[2:]
        runpy.run_path(tool, run_name="__main__")


if __name__ == "__main__":
    main()
