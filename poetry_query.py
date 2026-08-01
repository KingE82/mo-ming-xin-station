#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诗词查询引擎（本地 SQLite，31万首宋词 + 2万首唐诗 + 诗经305篇 + 论语）
用法: python3 poetry_query.py <关键词> [--author 作者] [--top N]
"""
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "static", "poetry.db")

# 表结构（转换时列名是 c0,c1...）
# poetry: c0=id c1=author_id c2=title c3=content(诗句|分隔) c4=平仄 c5=作者 c6=类型
# poems:  c0=id c1=author_id c2=title c3=content c4=作者
# shijing: c0=id c1=title c2=类别 c3=风/雅 c4=content
# lunyu:  c0=id c1=chapter c2=content


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _convert_variants(keyword):
    """生成简繁变体（zhconv）"""
    variants = {keyword}
    try:
        from zhconv import convert
        variants.add(convert(keyword, 'zh-cn'))  # 繁→简
        variants.add(convert(keyword, 'zh-tw'))  # 简→繁
    except Exception:
        pass
    return list(variants)


def search_poem(keyword, top=5):
    """按关键词搜诗词正文（支持简繁）"""
    conn = _connect()
    results = []
    variants = _convert_variants(keyword)
    try:
        for v in variants:
            rows = conn.execute(
                "SELECT rowid, c2 AS title, c5 AS author, c3 AS content FROM poetry "
                "WHERE c3 LIKE ? LIMIT ?",
                (f"%{v}%", top),
            ).fetchall()
            for r in rows:
                results.append({
                    "type": "诗词",
                    "title": r["title"],
                    "author": r["author"] or "",
                    "content": (r["content"] or "").replace("|", "\n"),
                    "rowid": r["rowid"],
                })
    except Exception:
        pass

    if len(results) < top:
        try:
            rows = conn.execute(
                "SELECT rowid, c2 AS title, c4 AS author, c3 AS content FROM poems "
                "WHERE c3 LIKE ? LIMIT ?",
                (f"%{keyword}%", top - len(results)),
            ).fetchall()
            for r in rows:
                results.append({
                    "type": "唐诗",
                    "title": r["title"],
                    "author": r["author"] or "",
                    "content": (r["content"] or "").replace("|", "\n"),
                    "rowid": r["rowid"],
                })
        except Exception:
            pass

    conn.close()
    return results


def search_poem_by_title(title_keyword, top=5):
    """按标题搜"""
    conn = _connect()
    results = []
    for tbl, c_author, c_title, c_content, typ in [
        ("poetry", "c5", "c2", "c3", "宋词"),
        ("poems", "c4", "c2", "c3", "唐诗"),
    ]:
        try:
            rows = conn.execute(
                f"SELECT rowid, {c_title} AS title, {c_author} AS author, {c_content} AS content "
                f"FROM {tbl} WHERE {c_title} LIKE ? LIMIT ?",
                (f"%{title_keyword}%", top),
            ).fetchall()
            for r in rows:
                results.append({
                    "type": typ,
                    "title": r["title"],
                    "author": r["author"] or "",
                    "content": (r["content"] or "").replace("|", "\n"),
                    "rowid": r["rowid"],
                })
        except Exception:
            pass
    conn.close()
    return results


def search_by_author(author, top=5):
    """按作者搜"""
    conn = _connect()
    results = []
    try:
        rows = conn.execute(
            "SELECT rowid, c2 AS title, c5 AS author, c3 AS content FROM poetry "
            "WHERE c5 LIKE ? LIMIT ?",
            (f"%{author}%", top),
        ).fetchall()
        for r in rows:
            results.append({
                "type": "宋词",
                "title": r["title"],
                "author": r["author"] or "",
                "content": (r["content"] or "").replace("|", "\n"),
                "rowid": r["rowid"],
            })
    except Exception:
        pass
    conn.close()
    return results


def search_shijing(keyword, top=5):
    """搜诗经"""
    conn = _connect()
    results = []
    try:
        rows = conn.execute(
            "SELECT rowid, c1 AS title, c4 AS content FROM shijing WHERE c4 LIKE ? LIMIT ?",
            (f"%{keyword}%", top),
        ).fetchall()
        for r in rows:
            results.append({
                "type": "诗经",
                "title": r["title"],
                "author": "诗经",
                "content": (r["content"] or "").replace("|", "\n"),
                "rowid": r["rowid"],
            })
    except Exception:
        pass
    conn.close()
    return results


def search_lunyu(keyword, top=3):
    """搜论语（支持简繁）"""
    conn = _connect()
    results = []
    variants = _convert_variants(keyword)
    try:
        for v in variants:
            rows = conn.execute(
                "SELECT rowid, c1 AS chapter, c2 AS content FROM lunyu WHERE c2 LIKE ? LIMIT ?",
                (f"%{v}%", top),
            ).fetchall()
            for r in rows:
                results.append({
                    "type": "论语",
                    "title": r["chapter"],
                    "author": "孔子",
                    "content": (r["content"] or "").replace("|", "\n"),
                    "rowid": r["rowid"],
                })
    except Exception:
        pass
    conn.close()
    return results


def get_poem_full(title, author, typ="", rowid=None):
    """按 rowid（优先）或 标题+作者 定位一首诗，返回完整内容（详情页用）"""
    def _norm(s):
        return (s or "").replace(" ", "").strip()

    conn = _connect()
    try:
        def _query(sql, params):
            row = conn.execute(sql, params).fetchone()
            if row:
                return {"type": row["type"], "title": row["title"], "author": row["author"],
                        "content": (row["content"] or "").replace("|", "\n")}
            return None

        # 0. rowid 精确查（最可靠，同题多首不会取错）
        if rowid:
            try:
                rid = int(rowid)
            except Exception:
                rid = None
            if rid:
                r = _query(
                    "SELECT '唐诗' AS type, c2 AS title, c4 AS author, c3 AS content "
                    "FROM poems WHERE rowid = ? LIMIT 1", (rid,))
                if r: return r
                r = _query(
                    "SELECT '宋词' AS type, c2 AS title, c5 AS author, c3 AS content "
                    "FROM poetry WHERE rowid = ? LIMIT 1", (rid,))
                if r: return r

        t_norm = _norm(title)
        a_norm = _norm(author)
        # 1. 按指定类型精确查
        if typ == "诗经":
            r = _query(
                "SELECT '诗经' AS type, c1 AS title, '诗经' AS author, c4 AS content "
                "FROM shijing WHERE c1 LIKE ? LIMIT 1", (f"%{t_norm}%",))
            if r: return r
        elif typ == "论语":
            from zhconv import convert
            t_tw = convert(t_norm, 'zh-tw')
            r = _query(
                "SELECT '论语' AS type, c1 AS title, '孔子' AS author, c2 AS content "
                "FROM lunyu WHERE c1 LIKE ? OR c1 LIKE ? LIMIT 1", (f"%{t_norm}%", f"%{t_tw}%"))
            if r: return r
        elif typ == "唐诗":
            r = _query(
                "SELECT '唐诗' AS type, c2 AS title, c4 AS author, c3 AS content "
                "FROM poems WHERE c2 LIKE ? AND (c4 LIKE ? OR ? = '') LIMIT 1",
                (f"%{t_norm}%", f"%{a_norm}%", a_norm))
            if r: return r
        else:
            r = _query(
                "SELECT '宋词' AS type, c2 AS title, c5 AS author, c3 AS content "
                "FROM poetry WHERE c2 LIKE ? AND (c5 LIKE ? OR ? = '') LIMIT 1",
                (f"%{t_norm}%", f"%{a_norm}%", a_norm))
            if r: return r
        # 2. 兑底：poems 表也试试（数据源分类不准，苏轼水调歌头在 poems 表）
        r = _query(
            "SELECT '唐诗' AS type, c2 AS title, c4 AS author, c3 AS content "
            "FROM poems WHERE c2 LIKE ? AND (c4 LIKE ? OR ? = '') LIMIT 1",
            (f"%{t_norm}%", f"%{a_norm}%", a_norm))
        if r: return r
        # 3. 最后兑底：poetry 表
        r = _query(
            "SELECT '宋词' AS type, c2 AS title, c5 AS author, c3 AS content "
            "FROM poetry WHERE c2 LIKE ? AND (c5 LIKE ? OR ? = '') LIMIT 1",
            (f"%{t_norm}%", f"%{a_norm}%", a_norm))
        if r: return r
    except Exception:
        pass
    finally:
        conn.close()
    return None


def format_results(results):
    """格式化输出"""
    if not results:
        return "未找到相关诗词。"
    out = []
    for i, r in enumerate(results[:5], 1):
        out.append(f"### {i}. [{r['type']}] {r['title']} — {r['author']}")
        out.append(r["content"][:500])
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 poetry_query.py <关键词>")
        sys.exit(1)
    kw = sys.argv[1]
    print(f"== 正文搜索 '{kw}' ==")
    print(format_results(search_poem(kw)))
    print(f"\n== 标题搜索 '{kw}' ==")
    print(format_results(search_poem_by_title(kw)))
    print(f"\n== 诗经 '{kw}' ==")
    print(format_results(search_shijing(kw)))
