---
name: anki-card-maker
description: 制作 Anki 记忆卡片（.apkg 文件或可粘贴文本）。当用户要求把单词、公式、知识点、笔记、错题等做成 Anki 卡片/记忆卡片/闪卡，或要求生成 apkg 文件、Anki 牌组、卡片导入 Anki，或询问如何把内容转成 Anki 卡时使用。支持问答题（正反卡）与 Cloze 挖空卡，可生成标准新版格式 .apkg（Anki 2.1.50+/26.x 直接导入），也可输出制表符分隔文本供手动导入。覆盖单词卡、数学公式（LaTeX）、概念问答、错题整理等场景。
---

# Anki Card Maker

将任意学习内容制作成 Anki 卡片，交付 `.apkg` 文件（推荐）或可粘贴文本。

## 工作流

1. **解析输入**：读取用户提供的单词列表、笔记、图片、公式、错题等，提取知识点。
2. **确定卡片类型**：
   - 默认用**问答题**（正面问题 → 背面答案），适合公式、概念、错题。
   - 背单词/挖空场景用 **Cloze**（`{{c1::...}}`）。
3. **设计内容**：每张卡片正面简短提问，背面给答案；公式用 LaTeX 包裹 `\[...\]`（行间）或 `\(...\)`（行内）。
4. **交付**：
   - 用户要文件 → 用 `scripts/build_apkg.py` 生成 .apkg（见下）。
   - 用户只要文本 → 输出制表符分隔文本（正面\t背面），并说明导入方法（桌面端 文件→导入，分隔符选制表符）。

## 生成 .apkg（推荐）

1. 把卡片数据写成 JSON 文件，结构：
```json
{
  "deck_name": "考研::数学::极限",
  "model": "qa",
  "notes": [
    {"front": "\\[x\\to 0,\\ \\sin x \\sim ?\\]", "back": "\\[x\\]", "tags": " 数学::极限 "}
  ]
}
```
   - `deck_name` 支持 `父::子` 层级；`model` 填 `qa`（问答题）或 `cloze`（挖空）。
   - `notes` 每项：`front` 正面、`back` 背面、`tags` 可选（格式 ` 标签 ` 前后带空格）。
   - JSON 中 LaTeX 反斜杠必须写成 `\\`（JSON 转义）。
2. 运行脚本：
```
python scripts/build_apkg.py input.json output.apkg [--deck-name "卡组名"]
```
   （`--deck-name` 可覆盖 JSON 里的卡组名）
3. 交付 .apkg 文件，并提示：桌面 Anki 文件→导入；手机 AnkiDroid 菜单→导入。

## 添加单词发音（TTS 音频）

背单词场景可给卡片加美式发音：

1. 先运行 `scripts/tts_audio.py` 为每个 front 生成 MP3，并自动把 `audio` 字段写入 input.json：
```
python scripts/tts_audio.py input.json --out-dir audio
```
   （默认女声 `en-US-JennyNeural`，可用 `--voice en-US-GuyNeural` 换男声）
2. 再用 `--media-dir` 打包，音频自动嵌入 apkg，背面附加 `[sound:xx.mp3]`：
```
python scripts/build_apkg.py input.json output.apkg --media-dir audio
```
3. 卡片导入 Anki 后背面会显示喇叭图标，点击播放发音。

## Cloze 挖空卡

- `model: "cloze"`，`front` 内含 `{{c1::挖空内容}}`，如 `单词 {{c1::apple}} 的中文是？`；`back` 可放额外注释（可留空）。
- 一个 front 内多个挖空用 `{{c1::..}} {{c2::..}}` 生成多张卡。

## 制卡质量要点

- 卡片要**小而聚焦**：一张卡只问一个点，避免信息过载。
- 数学/公式类优先 LaTeX，保持与 Anki 标准模板一致；提醒用户 Anki 需开启 LaTeX 渲染（默认开启）。
- 按主题组织卡组层级（如 `科目::章节::小节`），便于复习。
- 批量内容逐条核对，避免错字、漏卡、公式转义错误。

## 导入提示（交付时附带）

- **桌面 Anki**：文件 → 导入 → 选 .apkg，直接完成。
- **AnkiDroid（安卓）**：右上角菜单 → 导入 → 选 .apkg。
- **AnkiMobile（苹果）**：文件导入需先同步 AnkiWeb，或电脑导入后同步。
- 若报 "需要较新版本/JsonError"，确认用户拿到的是最新交付的 .apkg（标准结构只含 `collection.anki21` + `media`，media 为 `{}`）。
