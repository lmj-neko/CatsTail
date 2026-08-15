#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import os
import time
import logging
import keyboard
import ctypes
import pyperclip

# ---------- 提权 ----------
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    script = os.path.abspath(sys.argv[0])
    params = ' '.join(sys.argv[1:])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)

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
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
except Exception as e:
    logger.error(f"配置文件加载失败: {e}")
    sys.exit(1)

TRIGGER_CHARS = set(config.get('trigger_chars', []))
INSERT_PREFIX = config.get('insert_prefix', '')

if not TRIGGER_CHARS or not INSERT_PREFIX:
    logger.error("配置错误：trigger_chars 或 insert_prefix 为空")
    sys.exit(1)

# 标点符号集合（中英文）
PUNCTUATION = set('，。、；：！？…—·,.!?;:~@#$%^&*()_+{}|:"<>')  # 包含 ~ 等

logger.info(f"触发字符: {TRIGGER_CHARS}")
logger.info(f"插入前缀: {INSERT_PREFIX}")

# ---------- 需要 Shift 的符号映射 ----------
SHIFT_MAP = {
    '!': 'shift+1',
    '@': 'shift+2',
    '#': 'shift+3',
    '$': 'shift+4',
    '%': 'shift+5',
    '^': 'shift+6',
    '&': 'shift+7',
    '*': 'shift+8',
    '(': 'shift+9',
    ')': 'shift+0',
    '_': 'shift+-',
    '+': 'shift+=',
    '{': 'shift+[',
    '}': 'shift+]',
    '|': 'shift+\\',
    ':': 'shift+;',
    '"': "shift+'",
    '<': 'shift+,',
    '>': 'shift+.',
    '?': 'shift+/',
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
        # 普通字符（如 . , 等）
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

    # 如果不是触发字符，更新 _last_user_char 并放行
    if char not in TRIGGER_CHARS:
        # 忽略修饰键（shift, ctrl 等）
        if len(char) == 1 or char == '\n':
            _last_user_char = char
        return True

    # 触发字符处理
    logger.info(f"触发字符 '{repr(char)}' 被按下")

    # 判断是否跳过插入
    skip = False
    if _last_user_char in PUNCTUATION:
        logger.info(f"上一个字符 '{_last_user_char}' 是标点，跳过插入")
        skip = True
    elif _last_user_char == INSERT_PREFIX:
        logger.info(f"上一个字符 '{_last_user_char}' 是插入前缀，跳过插入")
        skip = True

    if skip:
        # 放行原按键，更新 _last_user_char
        _last_user_char = char
        return True

    # 需要插入
    logger.info(f"将插入前缀 '{INSERT_PREFIX}'")
    _simulating = True
    try:
        paste_text(INSERT_PREFIX)
        # 输入原触发字符
        type_char(char)
        time.sleep(0.02)
        _last_user_char = char   # 插入后，最终字符是触发字符
        logger.info(f"已插入 '{INSERT_PREFIX}' 和触发字符")
    except Exception as e:
        logger.error(f"模拟输入失败: {e}")
        _last_user_char = char   # 即使失败也更新，避免状态混乱
    finally:
        _simulating = False

    # 抑制原按键
    return False

# ---------- 启动 ----------
if __name__ == "__main__":
    logger.info("开始监听，按 Ctrl+Shift+Esc 可强制退出")
    keyboard.hook(on_key, suppress=True)
    keyboard.wait()