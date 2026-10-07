# -*- coding: utf-8 -*-
"""
============================================================
 步骤 3a：封装大模型调用
 学什么：
   - 怎么把"数据字典 + 指标口径"喂给大模型，让它生成 SQL（Text-to-SQL）
   - Prompt 是这个项目的核心资产，调 Prompt 就是这个岗位的日常
   - DeepSeek API 是 OpenAI 兼容协议，换 ChatGPT/Qwen 只改 base_url
 配置：
   - 环境变量 DEEPSEEK_API_KEY 里放你的 key
   - 不会配的话，直接把 key 填到下面 DEFAULT_KEY（别把代码传到 GitHub）
============================================================
"""
import os
import json
import requests

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "在这里填你的DeepSeek key")
BASE_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"

def build_sql_prompt(user_question: str, metrics_yaml_text: str) -> list:
    """
    这是最关键的 Prompt：
      1. 告诉模型表结构（从 metrics.yaml 读）
      2. 告诉模型指标怎么算
      3. 要求它只输出 SQL，不要废话
    """
    system = f"""你是一个 BI 数据助手，把用户的中文问题翻译成 SQLite SQL。

【数据库表结构与指标口径】
{metrics_yaml_text}

【输出要求】
1. 只输出一条可执行的 SQLite SELECT 语句，不要任何解释、不要 markdown 代码块。
2. 不要使用分号以外的多余符号。
3. 时间范围如果用户没说，就用 2025-04-01 到 2025-06-30（最近3个月）。
4. 如果用户问"营收"，就用指标字典里的口径；不要自己造聚合方式。
"""
    return [
        {"role": "system", "content": system},
        {"role": "user",   "content": user_question},
    ]

def ask_llm(messages: list) -> str:
    """调一次大模型，返回文本"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0,   # SQL 任务要稳定，温度设 0
    }
    r = requests.post(BASE_URL, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def build_summary_prompt(question: str, sql: str, rows: list, columns: list) -> str:
    """拿到 SQL 结果后，再让大模型用大白话总结一下"""
    return f"""用户问：{question}
执行的 SQL：{sql}
查询结果（列：{columns}）：
{rows}

请用 2-3 句大白话把结果讲清楚，不要念数字，直接说结论。"""
