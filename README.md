# anki-card-maker

将任意学习内容制作成 Anki 记忆卡片的技能（Skill），支持生成标准 `.apkg` 文件直接导入 Anki。

## 功能特性

- **问答题卡片**：正面问题 → 背面答案，适合公式、概念、错题
- **Cloze 挖空卡片**：`{{c1::挖空内容}}` 格式，适合单词、知识点填空
- **TTS 发音**：基于微软 Edge TTS 生成美式英语发音 MP3，自动嵌入卡片
- **层级卡组**：支持 `科目::章节::小节` 多级卡组结构
- **LaTeX 公式**：数学公式用标准 Anki LaTeX 渲染
- **标准 .apkg 格式**：Anki 2.1.50+ / 26.x 直接导入

## 目录结构

```
anki-card-maker/
├── SKILL.md                    # 技能定义文件（豆包/Doubao Agent 加载用）
├── README.md                   # 本文件
├── requirements.txt            # Python 依赖
└── scripts/
    ├── build_apkg.py           # 从 JSON 生成 .apkg 文件
    └── tts_audio.py            # 为单词生成 TTS 发音 MP3
```

## 快速开始

### 1. 准备卡片数据

创建 `cards.json`：

```json
{
  "deck_name": "考研::数学::极限",
  "model": "qa",
  "notes": [
    {
      "front": "\\[x\\to 0,\\ \\sin x \\sim ?\\]",
      "back": "\\[x\\]",
      "tags": " 数学::极限 "
    }
  ]
}
```

### 2. 生成 .apkg 文件

```bash
python scripts/build_apkg.py cards.json output.apkg
```

### 3. 导入 Anki

- **桌面 Anki**：文件 → 导入 → 选 `.apkg`
- **AnkiDroid（安卓）**：菜单 → 导入
- **AnkiMobile（苹果）**：电脑导入后同步 AnkiWeb

## Cloze 挖空卡示例

```json
{
  "deck_name": "英语::单词",
  "model": "cloze",
  "notes": [
    {
      "front": "单词 {{c1::apple}} 的中文是？",
      "back": "苹果"
    }
  ]
}
```

## 添加 TTS 发音

```bash
# 1. 先生成发音 MP3
python scripts/tts_audio.py cards.json --out-dir audio

# 2. 再打包（音频自动嵌入 apkg）
python scripts/build_apkg.py cards.json output.apkg --media-dir audio
```

可选参数：
- `--voice en-US-JennyNeural`（女声，默认）
- `--voice en-US-GuyNeural`（男声）

## 作为 Doubao Skill 使用

将本目录放入你的技能目录，Doubao Agent 会自动读取 `SKILL.md` 并在需要制作 Anki 卡片时调用。

## 依赖

- Python 3.8+
- edge-tts（仅 TTS 功能需要）

安装依赖：
```bash
pip install -r requirements.txt
```

## License

MIT
