import os
import uuid
import pandas as pd
from typing import List, Dict, Tuple

def load_reviews_from_file(file_path: str) -> Tuple[List[Dict], pd.DataFrame]:
    """
    智能读取本地 Excel/CSV 并进行模糊列名嗅探清洗

    返回:
        Tuple[List[Dict], pd.DataFrame]:
            - reviews: 评论列表（包含所有原始列 + 标准化字段）
            - original_df: 原始DataFrame（用于后续保存时保留所有列）
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"找不到文件: {file_path}")

    # 支持多种格式读取
    if file_path.endswith('.csv'):
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(file_path, encoding='utf-8-sig')
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding='gbk')
    elif file_path.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file_path)
    else:
        raise ValueError("仅支持 .csv, .xls, .xlsx 格式文件！")

    # 计算物理行数 (用于对账说明)
    physical_lines = 0
    if file_path.endswith('.csv'):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                physical_lines = sum(1 for _ in f)
        except Exception:
            physical_lines = len(df) + 1 # 降级方案
    else:
        physical_lines = len(df) + 1

    print(f"📄 成功加载表格：检测到 {len(df)} 条有效评论记录 (分布在 {physical_lines} 个物理行中)")
    if physical_lines > len(df) + 1:
        print(f"   💡 提示: 检测到评论正文内含有换行符，系统已自动合并处理。")

    # 模糊列名映射字典
    body_keywords = ['内容', '评价', '正文', 'review', 'body', 'text', 'content']
    rating_keywords = ['星级', '打分', '评分', 'rating', 'star', 'score']
    date_keywords = ['时间', '日期', 'date', 'time']

    # 嗅探函数
    def find_column(keywords):
        for col in df.columns:
            col_lower = str(col).lower()
            if any(kw in col_lower for kw in keywords):
                return col
        return None

    body_col = find_column(body_keywords)
    if not body_col:
        raise Exception(f"❌ 解析失败：表头中找不到包含以下关键词的评论主体列: {body_keywords}")

    rating_col = find_column(rating_keywords)
    date_col = find_column(date_keywords)

    print(f"🔍 字段映射成功 -> 内容列: '{body_col}' | 评分列: '{rating_col or '未找到'}' | 时间列: '{date_col or '未找到'}")

    reviews = []
    dropped_count = 0

    for idx, row in df.iterrows():
        body_text = str(row[body_col]).strip()

        # 黑洞数据清洗：跳过 NaN，跳过过短或纯字符
        if pd.isna(row[body_col]) or body_text.lower() == 'nan' or len(body_text) < 3:
            dropped_count += 1
            continue

        # 评分默认 0，时间默认留空
        try:
            rating_val = float(row[rating_col]) if rating_col and pd.notna(row[rating_col]) else 0.0
        except (ValueError, TypeError):
            rating_val = 0.0

        date_val = str(row[date_col]) if date_col and pd.notna(row[date_col]) else ""

        # 构建评论对象：保留所有原始列 + 添加标准化字段
        review_item = {
            "_original_data": dict(row),  # 保存原始数据的完整副本
            "review_id": str(uuid.uuid4())[:12],
            "body": body_text,
            "rating": rating_val,
            "date": date_val
        }
        reviews.append(review_item)

    print(f"🧹 清洗完毕 -> 有效提取: {len(reviews)} 条记录 (跳过无效/过短评论: {dropped_count} 条)")
    print(f"📊 原始列保留: {list(df.columns)}")

    return reviews, df


if __name__ == "__main__":
    # 为了防止人类看懵，用脚本内置的一条 Dummy CSV 取代
    dummy_csv = "data/dummy_test.csv"
    os.makedirs("data", exist_ok=True)
    with open(dummy_csv, "w", encoding="utf-8") as f:
        f.write("顾客名称,商品评价正文,商品星级,时间记录\n")
        f.write("张三,这个键盘手感太棒了！物流也快,5,2026-03-01\n")
        f.write("李四,质量差，按键不回弹,1,2026-03-02\n")
        f.write("王五,,5,\n")  # 该行应被清洗
        f.write("赵六,好,,2026-03-03\n")   # 该行被清洗(长度<3)，测试长度拦截
        f.write("A1,Not bad for the price.,4,2026-03-01\n")

    print(f"==== 开始执行 data_loader.py 冒烟测试 ====")
    res = load_reviews_from_file(dummy_csv)
    print("\n==== 抽样第一条有效数据 ====")
    import json
    if res:
        print(json.dumps(res[0], indent=2, ensure_ascii=False))
