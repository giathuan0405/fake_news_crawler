import pandas as pd
import glob

# 1) Liệt kê tất cả file CSV cần gộp
file_list = [
    "data_baochinhphu.csv",
    "data_dantri.csv",
    "data_nld.csv",
    "data_thanhnien.csv",
    "data_tuoitre.csv",
    "data_vnexpress.csv",
]

# 2) Đọc và gộp tất cả vào một DataFrame
df_list = []
for file in file_list:
    df = pd.read_csv(file, encoding="utf-8-sig")
    df_list.append(df)

merged_df = pd.concat(df_list, ignore_index=True)

# 3) Cập nhật lại cột stt từ 1 -> N
merged_df["stt"] = range(1, len(merged_df) + 1)

# 4) Ghi ra file CSV mới
merged_df.to_csv("data_uytin.csv", index=False, encoding="utf-8-sig")

print(f"Đã gộp {len(file_list)} file vào data_uytin.csv với {len(merged_df)} bài viết.")
