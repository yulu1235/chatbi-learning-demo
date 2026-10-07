# -*- coding: utf-8 -*-
"""
============================================================
 把 UCI Online Retail 真数据洗进 SQLite
 学什么：
   - 真实业务数据有多脏：有缺失、有退货、有取消订单
   - 数据清洗是 BI 项目 70% 的工作量
 数据说明：
   - 英国一家在线零售商 2010/12 - 2011/12 的真实交易
   - 54 万行原始记录，去掉无效后约 40 万行有效销售
============================================================
"""
import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent
XLSX = ROOT / "online_retail.xlsx"
DB   = ROOT / "retail.db"

def build():
    print("[1/4] 读 Excel ...")
    df = pd.read_excel(XLSX)
    print(f"     原始行数: {len(df)}")

    # 规范列名
    df.columns = [c.strip() for c in df.columns]

    print("[2/4] 清洗 ...")
    before = len(df)
    # 1) 去掉 CustomerID 为空的（没登记客户的散客，做会员分析没用）
    df = df.dropna(subset=["CustomerID"])
    # 2) 去掉取消订单（InvoiceNo 以 C 开头）和退货（Quantity <= 0）
    df = df[~df["InvoiceNo"].astype(str).str.startswith("C")]
    df = df[df["Quantity"] > 0]
    # 3) 去掉单价 <= 0 的
    df = df[df["UnitPrice"] > 0]
    # 4) 算成交金额
    df["Amount"] = (df["Quantity"] * df["UnitPrice"]).round(2)
    # 5) 日期转成 YYYY-MM-DD
    df["Date"] = pd.to_datetime(df["InvoiceDate"]).dt.strftime("%Y-%m-%d")
    print(f"     清洗后行数: {len(df)} （去掉了 {before-len(df)} 行无效）")

    print("[3/4] 写入 SQLite ...")
    if DB.exists():
        DB.unlink()
    conn = sqlite3.connect(DB)
    df[["InvoiceNo","StockCode","Description","Quantity","UnitPrice",
        "Amount","Date","CustomerID","Country"]].to_sql(
        "fact_retail", conn, index=False, if_exists="replace"
    )
    # 建索引
    conn.execute("CREATE INDEX idx_date ON fact_retail(Date)")
    conn.execute("CREATE INDEX idx_customer ON fact_retail(CustomerID)")
    conn.execute("CREATE INDEX idx_country ON fact_retail(Country)")
    conn.execute("CREATE INDEX idx_stock ON fact_retail(StockCode)")
    conn.commit()

    print("[4/4] 看一眼结果 ...")
    for r in conn.execute("""
        SELECT Country, COUNT(DISTINCT CustomerID) AS 客户数,
               ROUND(SUM(Amount),0) AS 总销售额
        FROM fact_retail GROUP BY Country
        ORDER BY 总销售额 DESC LIMIT 8
    """):
        print("   ", r)
    conn.close()
    print(f"\n[OK] 数据库: {DB}")

if __name__ == "__main__":
    build()
