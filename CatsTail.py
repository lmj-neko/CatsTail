#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import logging
import ctypes
import pyperclip
import keyboard
import tkinter as tk
from tkinter import ttk

# ---------- 硬编码配置 ----------
CONFIG = {
    "trigger_chars": ["。", ".", "！", "!", "~", ",", "，", "\n"],
    "insert_prefix": "喵"
}

# ---------- 提权 ----------
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    script = os.path.abspath(sys.argv[0])
    params = ' '.join(sys.argv[1:])
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{script}" {params}', None, 1
    )

if not is_admin():
    print("请求管理员权限...")
    run_as_admin()
    sys.exit(0)

# ---------- 日志 ----------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler('insert.log', encoding='utf-8')]
)
logger = logging.getLogger(__name__)
logger.info("程序以管理员权限启动")

# ---------- 加载配置 ----------
TRIGGER_CHARS = set(CONFIG.get('trigger_chars', []))
INSERT_PREFIX = CONFIG.get('insert_prefix', '')

if not TRIGGER_CHARS or not INSERT_PREFIX:
    logger.error("配置错误：trigger_chars 或 insert_prefix 为空")
    sys.exit(1)

PUNCTUATION = set('，。、；：！？…—·,.!?;:~@#$%^&*()_+{}|:"<>')
logger.info(f"触发字符: {TRIGGER_CHARS}")
logger.info(f"插入前缀: {INSERT_PREFIX}")

# ---------- 需要 Shift 的符号映射 ----------
SHIFT_MAP = {
    '!': 'shift+1', '@': 'shift+2', '#': 'shift+3', '$': 'shift+4',
    '%': 'shift+5', '^': 'shift+6', '&': 'shift+7', '*': 'shift+8',
    '(': 'shift+9', ')': 'shift+0', '_': 'shift+-', '+': 'shift+=',
    '{': 'shift+[', '}': 'shift+]', '|': 'shift+\\', ':': 'shift+;',
    '"': "shift+'", '<': 'shift+,', '>': 'shift+.', '?': 'shift+/',
    '~': 'shift+`',
}

# ---------- 全局变量 ----------
_simulating = False
_last_user_char = ''   # 记录最近一次用户输入的字符（非模拟）

# ---------- 粘贴函数 ----------
def paste_text(text):
    old_clip = pyperclip.paste()
    try:
        pyperclip.copy(text)
        time.sleep(0.01)
        keyboard.release('shift')
        keyboard.release('ctrl')
        keyboard.release('alt')
        time.sleep(0.01)
        keyboard.press('ctrl')
        keyboard.press_and_release('v')
        keyboard.release('ctrl')
        time.sleep(0.02)
    finally:
        pyperclip.copy(old_clip)

# ---------- 输入单个字符（自动处理 Shift） ----------
def type_char(ch):
    if ch == '\n':
        keyboard.press_and_release('enter')
    elif ch in SHIFT_MAP:
        keyboard.press_and_release(SHIFT_MAP[ch])
    else:
        keyboard.press_and_release(ch)

# ---------- 按键回调 ----------
def on_key(event):
    global _simulating, _last_user_char
    if _simulating:
        return True

    if event.event_type != keyboard.KEY_DOWN:
        return True

    char = event.name
    if event.is_keypad or char == 'enter':
        char = '\n'

    if char not in TRIGGER_CHARS:
        if len(char) == 1 or char == '\n':
            _last_user_char = char
        return True

    logger.info(f"触发字符 '{repr(char)}' 被按下")

    skip = False
    if _last_user_char in PUNCTUATION:
        logger.info(f"上一个字符 '{_last_user_char}' 是标点，跳过插入")
        skip = True
    elif _last_user_char == INSERT_PREFIX:
        logger.info(f"上一个字符 '{_last_user_char}' 是插入前缀，跳过插入")
        skip = True

    if skip:
        _last_user_char = char
        return True

    logger.info(f"将插入前缀 '{INSERT_PREFIX}'")
    _simulating = True
    try:
        paste_text(INSERT_PREFIX)
        type_char(char)
        time.sleep(0.02)
        _last_user_char = char
        logger.info(f"已插入 '{INSERT_PREFIX}' 和触发字符")
    except Exception as e:
        logger.error(f"模拟输入失败: {e}")
        _last_user_char = char
    finally:
        _simulating = False

    return False  # 抑制原按键

# ---------- Tkinter 控制台 ----------
class CatTailConsole:
    def __init__(self, root):
        self.root = root
        root.title("猫尾巴")
        root.geometry("300x150")
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 状态变量
        self.enabled = tk.BooleanVar(value=False)

        # 界面组件
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 状态标签
        self.status_label = ttk.Label(main_frame, text="当前状态：已禁用", font=("Arial", 12))
        self.status_label.pack(pady=5)

        # 开关按钮
        self.toggle_btn = ttk.Button(
            main_frame,
            text="启用",
            width=15,
            command=self.toggle
        )
        self.toggle_btn.pack(pady=10)

        # 退出按钮
        quit_btn = ttk.Button(main_frame, text="退出程序", width=15, command=self.on_close)
        quit_btn.pack(pady=5)

        # 提示信息
        info_label = ttk.Label(main_frame, text="提示：启用后，在触发字符前自动插入“喵”", font=("Arial", 8))
        info_label.pack(pady=5)

    def toggle(self):
        if self.enabled.get():
            # 禁用
            keyboard.unhook_all()
            self.enabled.set(False)
            self.toggle_btn.config(text="启用")
            self.status_label.config(text="当前状态：已禁用")
            logger.info("用户手动禁用钩子")
        else:
            # 启用
            try:
                keyboard.hook(on_key, suppress=True)
                self.enabled.set(True)
                self.toggle_btn.config(text="禁用")
                self.status_label.config(text="当前状态：已启用")
                logger.info("用户手动启用钩子")
            except Exception as e:
                logger.error(f"启用钩子失败: {e}")
                # 如果失败，保持禁用状态
                self.enabled.set(False)
                self.toggle_btn.config(text="启用")
                self.status_label.config(text="当前状态：启用失败")
                # 显示错误消息
                tk.messagebox.showerror("错误", f"无法启用钩子：{e}")

    def on_close(self):
        # 如果钩子启用，先卸载
        if self.enabled.get():
            keyboard.unhook_all()
            logger.info("程序退出，钩子已卸载")
        self.root.destroy()
        sys.exit(0)

# ---------- 启动 ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = CatTailConsole(root)
    root.mainloop()