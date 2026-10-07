# -*- coding: utf-8 -*-
"""
============================================================
 步骤 1：造样例数据并写入 SQLite
 学什么：
   - 数仓/BI 里最经典的「星型模型」：一张事实表 + 多张维度表
   - 事实表 fact_sales：存"发生了什么"（每笔销售）
   - 维度表 dim_store：存"门店是什么"（编号、城市、区域）
   - 这种设计是观远、Tableau、Power BI 这类 BI 工具的数据底座
 为什么不用 MySQL：
   - SQLite 是一个文件就是一个数据库，零安装，双击就能开
   - 面试讲原理一样，代码把 sqlite3 换成 pymysql 就能连真 MySQL
============================================================
"""
import sqlite3
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)  # 固定随机种子，每次跑出来的数据一样，方便复现

DB_PATH = Path(__file__).parent / "retail.db"

# ---------- 1. 维度表：门店 ----------
# 20 家门店，分布在几个城市。真实项目里这张表一般由 CRM/ERP 系统同步过来。
STORES = [
    ("S001", "广州天河城店",  "广州", "天河"),
    ("S002", "广州正佳店",    "广州", "天河"),
    ("S003", "广州珠江新城店","广州", "珠江新城"),
    ("S004", "广州北京路店",  "广州", "越秀"),
    ("S005", "深圳南山店",    "深圳", "南山"),
    ("S006", "深圳福田店",    "深圳", "福田"),
    ("S007", "深圳罗湖店",    "深圳", "罗湖"),
    ("S008", "深圳宝安店",    "深圳", "宝安"),
    ("S009", "珠海香洲店",    "珠海", "香洲"),
    ("S010", "佛山南海店",    "佛山", "南海"),
    ("S011", "东莞南城店",    "东莞", "南城"),
    ("S012", "中山石岐店",    "中山", "石岐"),
    ("S013", "惠州惠城店",    "惠州", "惠城"),
    ("S014", "江门蓬江店",    "江门", "蓬江"),
    ("S015", "肇庆端州店",    "肇庆", "端州"),
    ("S016", "广州白云店",    "广州", "白云"),
    ("S017", "深圳龙岗店",    "深圳", "龙岗"),
    ("S018", "珠海金湾店",    "珠海", "金湾"),
    ("S019", "佛山禅城店",    "佛山", "禅城"),
    ("S020", "东莞东城店",    "东莞", "东城"),
]

# ---------- 2. 品类 ----------
CATEGORIES = ["饮料", "零食", "日用品", "乳制品", "烘焙"]

def build():
    if DB_PATH.exists():
        DB_PATH.unlink()  # 每次重跑，干净重建
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 维度表：门店
    cur.execute("""
        CREATE TABLE dim_store (
            store_id   TEXT PRIMARY KEY,   -- 门店编号
            store_name TEXT,               -- 门店名
            city       TEXT,               -- 城市
            district   TEXT                -- 区域
        )
    """)
    cur.executemany("INSERT INTO dim_store VALUES (?,?,?,?)", STORES)

    # 事实表：每天每店每个品类一行汇总（真实场景会更细，这里聚合到日）
    cur.execute("""
        CREATE TABLE fact_sales (
            sale_date   TEXT,            -- 销售日期 YYYY-MM-DD
            store_id    TEXT,            -- 门店编号，关联 dim_store
            category    TEXT,            -- 品类
            revenue     REAL,            -- 销售额（元）
            orders      INTEGER          -- 订单数
        )
    """)

    # 造 2025-01-01 ~ 2025-06-30 共 6 个月数据
    start = date(2025, 1, 1)
    end   = date(2025, 6, 30)
    rows = []
    d = start
    while d <= end:
        # 周末生意好一点，加个波动
        weekend_boost = 1.3 if d.weekday() >= 5 else 1.0
        for store_id, _name, _city, _dist in STORES:
            for cat in CATEGORIES:
                # 每店每天每品类一个数，加点随机和季节性
                base = 800 + random.random() * 1200
                seasonal = 1 + 0.2 * (d.month - 1) / 5  # 逐月微增
                revenue = round(base * weekend_boost * seasonal, 2)
                orders  = int(revenue / (25 + random.random() * 20))
                rows.append((d.isoformat(), store_id, cat, revenue, orders))
        d += timedelta(days=1)

    cur.executemany(
        "INSERT INTO fact_sales VALUES (?,?,?,?,?)", rows
    )

    # 建索引：BI 查得快的关键（面试可能问）
    cur.execute("CREATE INDEX idx_fact_date ON fact_sales(sale_date)")
    cur.execute("CREATE INDEX idx_fact_store ON fact_sales(store_id)")

    conn.commit()

    # 打印几行，让你直观看到数据长什么样
    print(f"[OK] 数据库已生成: {DB_PATH}")
    print(f"     门店数: {len(STORES)} | 事实表行数: {len(rows)}")
    print("\n样例数据（前 5 行）:")
    for r in cur.execute("""
        SELECT f.sale_date, s.store_name, f.category, f.revenue, f.orders
        FROM fact_sales f JOIN dim_store s ON f.store_id = s.store_id
        LIMIT 5
    """):
        print("   ", r)

    conn.close()

if __name__ == "__main__":
    build()
