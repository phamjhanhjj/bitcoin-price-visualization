# BTC Visualization (CoinGecko)

Hướng dẫn này hướng dẫn bạn cách chuẩn bị môi trường, lấy dữ liệu từ CoinGecko, xử lý dữ liệu thành OHLC/time-series, tính các chỉ số (returns, moving averages, volatility), và chạy dashboard tương tác bằng Streamlit.

Mọi script chính nằm trong thư mục `src/`.

Hướng dẫn nhanh (Windows PowerShell)

1) Tạo virtual environment và kích hoạt

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

2) Lấy dữ liệu mẫu từ CoinGecko

- Lưu ý: CoinGecko public API giới hạn truy vấn lịch sử đối với public users trong vòng 365 ngày. Nếu bạn cần lịch sử >365 ngày, xem phần "Lưu ý" phía dưới.

- Ví dụ: lấy 365 ngày gần nhất (dùng helper tiện lợi)

```powershell
python -c "from src.fetch_data import fetch_recent_market_chart; fetch_recent_market_chart('bitcoin','usd',365)"
```

- Hoặc lấy theo khoảng thời gian (range) — lưu ý hạn mức 365 ngày cho public API

```powershell
python -c "from src.fetch_data import fetch_market_chart_range; from datetime import datetime; fetch_market_chart_range('bitcoin','usd', datetime(2024,1,1), datetime(2024,12,31))"
```

3) Xử lý dữ liệu (parse → DataFrame → OHLC → feature)

```powershell
python -c "from src.process_data import process_and_save; process_and_save('data/raw/coingecko_bitcoin_market_chart_last365d.json')"
```

Lệnh trên sẽ tạo file processed (Parquet) trong `data/processed/`.

4) Chạy dashboard (Streamlit)

```powershell
streamlit run src/dashboard.py
```

Mở trình duyệt tới: http://localhost:8501

5) Các script phân tích & hình ảnh (tuỳ chọn)

- Sinh báo cáo nhanh (JSON + Markdown):

```powershell
python src/generate_analysis.py
```

- Sinh biểu đồ phân tích (histogram returns, volatility time series):

```powershell
python src/generate_plots.py
```

Các ảnh sẽ được lưu vào `docs/images/` và báo cáo Markdown ở `docs/code_and_data_analysis.md`.

Docker (tuỳ chọn)

Bạn có thể build image Docker và chạy Streamlit trong container:

```powershell
docker build -t btc-viz:latest .
docker run -p 8501:8501 --rm btc-viz:latest
```

Sau đó mở http://localhost:8501

Lưu ý & best practices

- Granularity & rate limits:
	- CoinGecko tự động điều chỉnh granularity cho các endpoint (ví dụ endpoint `ohlc` hay `market_chart/range` có thể trả nến theo tần suất khác nhau tuỳ khoảng thời gian). Public API giới hạn lịch sử tới 365 ngày; nếu cần dữ liệu dài hạn hoặc nến tần suất cao, cân nhắc dùng API của exchange (Binance) hoặc nâng cấp plan CoinGecko.

- Lưu raw JSON:
	- Luôn giữ bản raw JSON trong `data/raw/` để có thể debug và tái xử lý.

- Metadata:
	- Mỗi fetch sẽ lưu metadata trong `data/raw/meta/` (điều này giúp reproducibility).

- An toàn:
	- Không lưu API keys trong code. Dùng biến môi trường nếu cần.

Hỗ trợ và mở rộng

- Muốn so sánh nhiều coin: fetch và process tương ứng cho coin khác rồi mở dashboard, chọn nhiều file để so sánh.
- Muốn incremental historical fetch (tự động chỉ lấy phần thiếu): có thể thêm helper chunked/incremental fetcher (tôi có thể hỗ trợ).

Nếu bạn cần tôi triển khai thêm (ví dụ CI, deploy tự động, hay incremental fetcher), nói tôi biết và tôi sẽ làm tiếp.
