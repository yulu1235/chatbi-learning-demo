# -*- coding: utf-8 -*-
"""
============================================================
 步骤 3b：FastAPI 后端 —— 整个 ChatBI 的核心流程
 学什么：
   - 一个完整的接口从请求到返回经过哪几步
   - 怎么防止大模型生成危险 SQL（只允许 SELECT）
   - 怎么把"用户问题 → SQL → 数据 → 自然语言回答"串成一条链
 启动：
   python -m uvicorn app.main:app --reload --port 8000
   然后浏览器打开 http://localhost:8000
============================================================
"""
import sqlite3
from pathlib import Path

import yaml
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.llm import build_sql_prompt, ask_llm, build_summary_prompt

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "retail.db"
METRICS_PATH = ROOT / "metrics.yaml"

app = FastAPI(title="门店经营 ChatBI 演示")

# 把 static 目录（前端页面）挂成静态文件
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

class AskReq(BaseModel):
    question: str

def load_metrics_text() -> str:
    """把 metrics.yaml 读成文本，塞进 Prompt"""
    return METRICS_PATH.read_text(encoding="utf-8")

def run_sql(sql: str):
    """在 SQLite 里跑 SQL，返回 (列名, 行数据)"""
    # 安全限制：只允许 SELECT，防止大模型生成 DROP/DELETE
    sql_clean = sql.strip().rstrip(";")
    if not sql_clean.lower().startswith("select"):
        raise ValueError("出于安全只允许 SELECT 查询")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(sql_clean)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    conn.close()
    return cols, rows

@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")

@app.post("/api/ask")
def ask(req: AskReq):
    """
    核心接口：前端把用户问题发过来，后端走 3 步：
      1. 让大模型把中文问题翻译成 SQL
      2. 在数据库里执行 SQL
      3. 让大模型把结果翻译成大白话
    """
    metrics_text = load_metrics_text()

    # 第 1 步：生成 SQL
    messages = build_sql_prompt(req.question, metrics_text)
    sql = ask_llm(messages)

    # 第 2 步：执行 SQL
    try:
        cols, rows = run_sql(sql)
    except Exception as e:
        return {"ok": False, "sql": sql, "error": str(e)}

    # 第 3 步：自然语言总结
    summary = ask_llm([{"role": "user", "content": build_summary_prompt(
        req.question, sql, rows[:20], cols
    )}])

    return {
        "ok": True,
        "sql": sql,           # 把 SQL 返回给前端，让你看到 AI 到底查了啥
        "columns": cols,
        "rows": rows,
        "summary": summary,
    }
