# PIC18 Online Judge

PIC18F4520 組合語言的線上評測系統。提交的程式用 gpasm 組譯、gpsim 模擬，再比對暫存器或 RAM 的結果。

- 後端：FastAPI + PostgreSQL + RabbitMQ
- 前端：React + Vite
- 評測：每筆提交在獨立的 Docker 容器裡執行（無網路、唯讀、有時間限制）

## 啟動

需要 Docker（Engine 26 以上）和 Python 3。

```sh
python scripts/setup_env.py
docker build -t pic-judge .
docker compose up --build -d
docker compose exec api python -m scripts.create_admin
```

## 出題

測資是一個 zip，每組測資包含一個 gpsim 腳本（`.in`）和預期輸出（`.out`）。

`1.in`：

```
load /app/source.cod
step 3
dump r
cycles
quit
```

`1.out` 每行一個 `key=value`：

```
W = 05
```

`sample-data/` 裡有一組範例測資，另外有 AC、WA、CE 三份程式可以用來測試。

## 測試

```sh
cd backend
uv sync --frozen
uv run python -m pytest -q
```

```sh
cd frontend
npm ci
npm run build
npm run lint
```

## 安全性

評測沙箱：

- 每筆提交在獨立容器執行：無網路、唯讀檔案系統、移除所有 capabilities、以 nobody 身分執行
- 限制記憶體、CPU、程序數與執行時間

服務：

- JWT secret 和資料庫密碼沒有預設值，未設定時服務不會啟動
- 密碼以 bcrypt 雜湊儲存，登入有頻率限制
- 限制請求大小與原始碼長度

已知限制：

- Worker 需要存取 Docker socket 才能建立沙箱，等於擁有那台主機上 Docker 的控制權。要對外開放的話，建議：
  - 把 worker 放在專用的機器或 VM
  - 透過 docker-socket-proxy 限制 worker 可用的 Docker API
  - 在前面加 reverse proxy 提供 HTTPS
