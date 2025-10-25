import pandas as pd

# Đọc dữ liệu
df = pd.read_csv('data/tourism_vnat.csv')

# Kiểm tra 5 dòng đầu
print(df.head())

# Làm sạch dữ liệu (nếu cần)
df = df.dropna(subset=['Destination'])
df = df.drop_duplicates()

# Lưu lại bản đã xử lý
df.to_csv('data/tourism_clean.csv', index=False)
print("✅ Data cleaned and saved!")
