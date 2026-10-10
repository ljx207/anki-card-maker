#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tts_audio.py - 为单词/短语生成美式英语发音 MP3（微软 Edge TTS）。

用法:
    python tts_audio.py input.json [--out-dir audio] [--voice en-US-JennyNeural]

input.json: 与 build_apkg.py 相同结构, 读取每条 note 的 front 作为朗读文本。
输出: 每个 front 生成一个 MP3 文件, 文件名 = front 清洗后 + .mp3 (空格->_,
     非法字符删除)。同时更新 input.json 中每条 note 的 "audio" 字段,
     指向生成的音频文件名, 供 build_apkg.py --media-dir 使用。
"""
import json
import sys
import os
import re
import asyncio


def safe_filename(text: str) -> str:
    s = text.strip()
    s = re.sub(r'[\\/:*?"<>|\s]+', "_", s)
    s = re.sub(r"_+", "_", s)
    s = s.strip("_")
    return s


async def gen(text: str, out_path: str, voice: str):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)


def main():
    if len(sys.argv) < 2:
        print("用法: python tts_audio.py input.json [--out-dir audio] [--voice en-US-JennyNeural]")
        sys.exit(1)
    input_path = sys.argv[1]
    out_dir = "audio"
    voice = "en-US-JennyNeural"
    if "--out-dir" in sys.argv:
        out_dir = sys.argv[sys.argv.index("--out-dir") + 1]
    if "--voice" in sys.argv:
        voice = sys.argv[sys.argv.index("--voice") + 1]

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    notes = data.get("notes", [])
    os.makedirs(out_dir, exist_ok=True)

    tasks = []
    for n in notes:
        front = n.get("front", "")
        if not front:
            continue
        fname = safe_filename(front) + ".mp3"
        out_path = os.path.join(out_dir, fname)
        n["audio"] = fname
        tasks.append((front, out_path, voice, fname))

    async def run_all():
        for front, out_path, v, fname in tasks:
            await gen(front, out_path, v)
            print("OK:", fname)

    asyncio.run(run_all())

    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"done: {len(tasks)} audio -> {out_dir}")


if __name__ == "__main__":
    main()
