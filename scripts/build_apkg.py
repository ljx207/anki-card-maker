#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_apkg.py - 从 JSON 卡片数据构建标准新版 Anki .apkg 文件。

用法:
    python build_apkg.py input.json output.apkg [--deck-name "名字::子卡组"]

input.json 结构:
{
  "deck_name": "我的卡组",            # 可选, 默认 "AnkiSkill"
  "model": "cloze" | "qa",           # 可选, 默认 "qa" (问答题)
  "notes": [
    {"front": "sinx ~ ?", "back": "x", "tags": " 数学::极限 "},
    ...
  ]
}

规则:
- qa 模型: 正面 front, 背面 back, 模板 {{正面}} / {{背面}}
- cloze 模型: front 含 {{c1::...}} 挖空, back 可留空, 使用标准 Cloze 模板
- 公式建议用 LaTeX 包裹: \\[...\\] (行间) 或 \\(...\\) (行内), 需在 Anki 中开启 LaTeX
- 输出为标准新版格式 apkg (仅 collection.anki21 + media), Anki 2.1.50+ / 26.x 可直接导入
"""
import json
import sys
import os
import time
import hashlib
import base64
import zipfile
import sqlite3


def csum(field0: str) -> int:
    """Anki 笔记 checksum: sha1(field0)[:4] 的整数"""
    b = field0.encode("utf-8")
    return int.from_bytes(hashlib.sha1(b).digest()[:4], "big")


def new_guid() -> str:
    return base64.b64encode(os.urandom(9)).decode().replace("+", "-").replace("/", "_")[:8]


def make_qa_model() -> dict:
    """问答题模型 (正面/背面)"""
    return {
        "id": int(time.time() * 1000),
        "name": "问答题",
        "type": 0,
        "mod": int(time.time()),
        "usn": 0,
        "sortf": 0,
        "did": None,
        "tmpls": [
            {
                "name": "卡片 1", "ord": 0,
                "qfmt": "{{正面}}",
                "afmt": "{{FrontSide}}\n\n<hr id=answer>\n\n{{背面}}",
                "bqfmt": "", "bafmt": "", "did": None, "bfont": "", "bsize": 0,
                "id": -2324572822571593805,
            }
        ],
        "flds": [
            {"name": "正面", "ord": 0, "sticky": False, "rtl": False, "font": "Arial",
             "size": 20, "description": "", "plainText": False, "collapsed": False,
             "excludeFromSearch": False, "id": 7738181167939851904, "tag": None,
             "preventDeletion": False},
            {"name": "背面", "ord": 1, "sticky": False, "rtl": False, "font": "Arial",
             "size": 20, "description": "", "plainText": False, "collapsed": False,
             "excludeFromSearch": False, "id": 1195299837921992237, "tag": None,
             "preventDeletion": False},
        ],
        "css": ".card {\n    font-family: arial;\n    font-size: 20px;\n    text-align: center;\n    color: black;\n    background-color: white;\n}\n",
        "latexPre": "\\documentclass[12pt]{article}\n\\special{papersize=3in,5in}\n\\usepackage[utf8]{inputenc}\n\\usepackage{amssymb,amsmath}\n\\pagestyle{empty}\n\\setlength{\\parindent}{0in}\n\\begin{document}\n",
        "latexPost": "\\end{document}",
        "latexsvg": False,
        "req": [[0, "any", [0]]],
    }


def make_cloze_model() -> dict:
    """Cloze 挖空模型 (标准 Anki Cloze)"""
    return {
        "id": int(time.time() * 1000) + 1,
        "name": "Cloze",
        "type": 1,
        "mod": int(time.time()),
        "usn": 0,
        "sortf": 0,
        "did": None,
        "tmpls": [
            {
                "name": "Cloze", "ord": 0,
                "qfmt": "{{cloze:Text}}",
                "afmt": "{{cloze:Text}}\n\n<hr id=answer>\n\n{{Back Extra}}",
                "bqfmt": "", "bafmt": "", "did": None, "bfont": "", "bsize": 0,
                "id": -2324572822571593806,
            }
        ],
        "flds": [
            {"name": "Text", "ord": 0, "sticky": False, "rtl": False, "font": "Arial",
             "size": 20, "description": "", "plainText": False, "collapsed": False,
             "excludeFromSearch": False, "id": 1738181167939851904, "tag": None,
             "preventDeletion": False},
            {"name": "Back Extra", "ord": 1, "sticky": False, "rtl": False, "font": "Arial",
             "size": 20, "description": "", "plainText": False, "collapsed": False,
             "excludeFromSearch": False, "id": 1195299837921992240, "tag": None,
             "preventDeletion": False},
        ],
        "css": ".card {\n    font-family: arial;\n    font-size: 20px;\n    text-align: center;\n    color: black;\n    background-color: white;\n}\n",
        "latexPre": "\\documentclass[12pt]{article}\n\\special{papersize=3in,5in}\n\\usepackage[utf8]{inputenc}\n\\usepackage{amssymb,amsmath}\n\\pagestyle{empty}\n\\setlength{\\parindent}{0in}\n\\begin{document}\n",
        "latexPost": "\\end{document}",
        "latexsvg": False,
        "req": [[0, "any", [0]]],
    }


def main():
    if len(sys.argv) < 3:
        print("用法: python build_apkg.py input.json output.apkg [--deck-name 名字] [--media-dir 媒体目录]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    deck_name = None
    media_dir = None
    if "--deck-name" in sys.argv:
        i = sys.argv.index("--deck-name")
        deck_name = sys.argv[i + 1]
    if "--media-dir" in sys.argv:
        i = sys.argv.index("--media-dir")
        media_dir = sys.argv[i + 1]

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    deck_name = deck_name or data.get("deck_name", "AnkiSkill")
    model_kind = data.get("model", "qa").lower()
    notes = data.get("notes", [])

    # ---------- 创建数据库 ----------
    db_path = os.path.join(os.path.dirname(output_path) or ".", "collection.anki21")
    if os.path.exists(db_path):
        os.remove(db_path)
    db = sqlite3.connect(db_path)
    cur = db.cursor()

    # 表结构 (Anki schema 11)
    cur.executescript("""
    CREATE TABLE col (id integer primary key, crt integer not null, mod integer not null,
      scm integer not null, ver integer not null, dty integer not null, usn integer not null,
      ls integer not null, conf text not null, models text not null, decks text not null,
      dconf text not null, tags text not null);
    CREATE TABLE notes (id integer primary key, guid text not null, mid integer not null,
      mod integer not null, usn integer not null, tags text not null, flds text not null,
      sfld integer not null, csum integer not null, flags integer not null, data text not null);
    CREATE TABLE cards (id integer primary key, nid integer not null, did integer not null,
      ord integer not null, mod integer not null, usn integer not null, type integer not null,
      queue integer not null, due integer not null, ivl integer not null, factor integer not null,
      reps integer not null, lapses integer not null, left integer not null, odue integer not null,
      odid integer not null, flags integer not null, data text not null);
    CREATE TABLE revlog (id integer primary key, cid integer not null, usn integer not null,
      ease integer not null, ivl integer not null, lastIvl integer not null, factor integer not null,
      time integer not null, type integer not null);
    CREATE TABLE graves (usn integer not null, oid integer not null, type integer not null);
    CREATE INDEX ix_notes_usn on notes (usn);
    CREATE INDEX ix_cards_usn on cards (usn);
    CREATE INDEX ix_cards_nid on cards (nid);
    CREATE INDEX ix_cards_sched on cards (did, queue, due);
    CREATE INDEX ix_revlog_usn on revlog (usn);
    CREATE INDEX ix_cards_nid_1 on cards (nid, ord);
    """)

    now = int(time.time())
    now_ms = int(time.time() * 1000)
    model = make_cloze_model() if model_kind == "cloze" else make_qa_model()
    mid = model["id"]

    # 卡组: 支持 "父::子" 层级, 每层一个 deck
    decks = {}
    parts = [p for p in deck_name.split("::") if p]
    parent_id = 1  # Default
    deck_id_map = {"1": "Default"}
    for i, part in enumerate(parts):
        full_name = "::".join(parts[: i + 1])
        did = now_ms + i
        decks[str(did)] = {
            "id": did, "mod": now, "name": full_name, "usn": -1,
            "lrnToday": [0, 0], "revToday": [0, 0], "newToday": [0, 0],
            "timeToday": [0, 0], "collapsed": False, "browserCollapsed": False,
            "desc": "", "dyn": 0, "conf": 1, "extendNew": 0, "extendRev": 0,
            "reviewLimit": None, "newLimit": None,
            "reviewLimitToday": None, "newLimitToday": None,
        }
        deck_id_map[str(did)] = full_name
        parent_id = did
    decks.setdefault("1", {
        "id": 1, "mod": 0, "name": "Default", "usn": 0,
        "lrnToday": [0, 0], "revToday": [0, 0], "newToday": [0, 0],
        "timeToday": [0, 0], "collapsed": True, "browserCollapsed": True,
        "desc": "", "dyn": 0, "conf": 1, "extendNew": 0, "extendRev": 0,
        "reviewLimit": None, "newLimit": None, "reviewLimitToday": None,
        "newLimitToday": None,
    })
    dconf = {"1": {"id": 1, "mod": 0, "name": "Default", "usn": 0, "maxTaken": 60,
                   "autoplay": True, "timer": 0, "replayq": True,
                   "new": {"bury": False, "delays": [1, 10], "initialFactor": 2500,
                           "ints": [1, 4, 7], "order": 1, "perDay": 20},
                   "rev": {"bury": False, "ease4": 1.3, "fuzz": 0.05, "hardFactor": 1.2,
                           "ivlFct": 1.0, "maxIvl": 36500, "perDay": 200},
                   "lapse": {"leechAction": 0, "leechFails": 8, "minInt": 1,
                             "mult": 0.0},
                   "dyn": False}}
    cur.execute("INSERT INTO col (id,crt,mod,scm,ver,dty,usn,ls,conf,models,decks,dconf,tags) "
                "VALUES (1,?,?,?,11,0,0,0,?,?,?,?,'{}')",
                (int(time.time() - 100 * 365 * 86400), now, now,
                 json.dumps({"sched2021": True, "estTimes": True, "newSpread": 0,
                             "schedVer": 1, "timeLim": 0, "sortBackwards": False,
                             "collapseTime": 1200, "addToCur": True, "nextPos": 1,
                             "creationOffset": -600, "curDeck": 1, "dayLearnFirst": False,
                             "sortType": "noteFld", "activeDecks": [1], "curModel": mid,
                             "dueCounts": True}),
                 json.dumps({str(mid): model}, ensure_ascii=False),
                 json.dumps(decks, ensure_ascii=False),
                 json.dumps(dconf, ensure_ascii=False)))

    # ---------- 写入笔记与卡片 ----------
    # 收集媒体文件: {原始文件名: (在apkg内的文件名, 路径)}
    media_map = {}   # apkg内名(数字) -> 原始文件名
    media_files = [] # (apkg内名, 原始名, 路径)
    if media_dir and os.path.isdir(media_dir):
        for fn in sorted(os.listdir(media_dir)):
            p = os.path.join(media_dir, fn)
            if os.path.isfile(p) and not fn.startswith('.'):
                media_map[str(len(media_map))] = fn
                media_files.append((str(len(media_files)), fn, p))

    nid = now_ms + 1000
    due = 1
    for n in notes:
        front = n.get("front", "")
        back = n.get("back", "")
        tags = n.get("tags", "")
        # audio 字段: 在正面附加 [sound:原始文件名] (背单词时正面即可发音)
        audio = n.get("audio", "")
        if audio:
            front = front + " [sound:" + audio + "]"
        flds = front + "\x1f" + back
        cur.execute(
            "INSERT INTO notes (id,guid,mid,mod,usn,tags,flds,sfld,csum,flags,data) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (nid, new_guid(), mid, now, -1, tags, flds, front, csum(front), 0, ""))
        cur.execute(
            "INSERT INTO cards (id,nid,did,ord,mod,usn,type,queue,due,ivl,factor,reps,"
            "lapses,left,odue,odid,flags,data) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (nid, nid, parent_id, 0, now, -1, 0, 0, due, 0, 0, 0, 0, 0, 0, 0, 0, ""))
        due += 1
        nid += 1

    cur.execute("UPDATE col SET mod=?, scm=? WHERE id=1", (now, now))
    db.commit()
    db.close()

    # ---------- 打包 apkg ----------
    # media 文件: JSON 对象, key 为 apkg 内文件名(数字), value 为原始文件名
    media_path = os.path.join(os.path.dirname(db_path), "media")
    with open(media_path, "w", encoding="utf-8") as f:
        json.dump(media_map, f)
    if os.path.exists(output_path):
        os.remove(output_path)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(db_path, "collection.anki21")
        z.write(media_path, "media")
        # 媒体文件: 以数字为名打入 apkg
        for idx, orig, p in media_files:
            z.write(p, str(idx))
    os.remove(db_path)
    os.remove(media_path)
    print(f"OK: {len(notes)} notes, {len(media_files)} media -> {output_path}")


if __name__ == "__main__":
    main()
