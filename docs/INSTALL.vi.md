# Hướng dẫn cài đặt (tiếng Việt)

Bản tiếng Anh đầy đủ hơn (khắc phục sự cố, Kubernetes): [INSTALL.md](INSTALL.md).

> **Phạm vi.** NEXORA M0 chỉ cài **control plane** (API, giao diện web, PostgreSQL). Nó **không** cài Kafka,
> Flink, Spark, Trino, Iceberg… — các engine đó chạy trên hạ tầng riêng và được đăng ký trong NEXORA như
> "connection". Xem [PROJECT_STATUS](status/PROJECT_STATUS.md).

## 1. Máy phát triển (không cần Docker/Kubernetes)

Yêu cầu: Git, **Python 3.11**, **Node.js ≥ 22**.

```bash
git clone https://github.com/tuannt2906/nexora-platform.git
cd nexora-platform
python tools/nx.py setup     # tạo .venv từ lock file có hash, cài package, npm ci
python tools/nx.py check     # lint, typecheck, test, validate, build, security
```

Windows không có `make`: dùng `python tools/nx.py <target>`. Công cụ nào chưa cài (Helm, Docker, PostgreSQL) sẽ
hiện **SKIP** rõ ràng ở máy local và bị tính là **lỗi** khi `CI=true`. Chạy API cục bộ: xem mục tương ứng trong
[INSTALL.md](INSTALL.md#run-the-api-and-the-ui-locally-light-sqlite).

## 2. Server chạy Docker Compose

Yêu cầu: Linux có **Docker Engine ≥ 24** + **Compose v2**, `git`, `openssl`, `python3`, truy cập HTTPS tới `ghcr.io`.

```bash
# 1) lấy mã nguồn đúng bản release (SHA này chính là tag của image)
sudo git clone https://github.com/tuannt2906/nexora-platform.git /opt/nexora
cd /opt/nexora && git fetch --tags && git checkout --detach v0.1.0
git rev-parse HEAD                      # ghi lại SHA đầy đủ

# 2) file bí mật nằm NGOÀI repo
sudo install -d -m 750 /etc/nexora
sudo cp deploy/compose/.env.example /etc/nexora/nexora.env && sudo chmod 600 /etc/nexora/nexora.env
sudo nano /etc/nexora/nexora.env
#   NEXORA_IMAGE_REGISTRY=ghcr.io/tuannt2906/nexora-platform
#   NEXORA_IMAGE_TAG=<SHA đầy đủ ở bước 1>
#   NEXORA_POSTGRES_PASSWORD=<openssl rand -hex 24>     (chỉ dùng ký tự A-Za-z0-9_-)
#   NEXORA_API_TOKEN=<openssl rand -hex 32>

# 3) chạy
cd deploy/compose
docker compose --env-file /etc/nexora/nexora.env pull
docker compose --env-file /etc/nexora/nexora.env up -d --wait

# 4) kiểm tra
cd /opt/nexora && set -a && . /etc/nexora/nexora.env && set +a
python3 tests/smoke/smoke.py --base-url http://127.0.0.1:${NEXORA_WEB_PORT:-8080} --token-env NEXORA_API_TOKEN
```

Kết quả mong đợi: `4/4 smoke checks passed` (mục metrics báo SKIP vì `/metrics` không được public qua web). Mở `http://<server>:8080`, dán `NEXORA_API_TOKEN`.

Lưu ý quan trọng:
- Image trên GHCR mặc định ở chế độ **private**. Sau lần release đầu tiên: đặt 2 package (`control-plane`, `web`)
  thành **Public**, hoặc `docker login ghcr.io -u tuannt2906` bằng PAT có quyền `read:packages`.
- Đặt reverse proxy TLS (Caddy/nginx/Traefik) trước cổng 8080 và chặn cổng 8080 bằng firewall. Không public `/metrics`.
- **Nâng cấp:** checkout tag mới, sửa `NEXORA_IMAGE_TAG`, `pull` rồi `up -d --wait`. **Rollback:** đặt lại SHA cũ.
  Sao lưu trước khi nâng cấp: [backup-restore.md](operations/backup-restore.md).
- **Chưa có release nào?** Chỉ để thử nghiệm, build từ mã nguồn trên server (không dùng cho production):
  đặt `NEXORA_IMAGE_REGISTRY=nexora-local`, `NEXORA_IMAGE_TAG=bootstrap`, rồi
  `docker compose -f docker-compose.yml -f docker-compose.dev.yml --env-file /etc/nexora/nexora.env up -d --build --wait`.

## 3. Kubernetes

Xem [INSTALL.md](INSTALL.md#3-kubernetes) và [deploy/kubernetes/README.md](../deploy/kubernetes/README.md). Chưa được thử trên cluster thật.

## 4. Người bảo trì: phát hành lần đầu

CI xanh trên `main` → `git tag v0.1.0 && git push origin v0.1.0` → workflow `release.yml` build/quét/publish image
và tạo GitHub Release → đặt package GHCR thành Public → làm theo mục 2.
