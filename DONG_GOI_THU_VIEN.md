# Đóng gói thư viện Python (`boc-tach-ban-ve`)

Mã nguồn vẫn nằm ở `backend/app` (Docker, `run.py` không đổi). Khi build wheel,
thư mục này được đổi tên thành package `boc_tach_ban_ve` — cấu hình ở
`backend/pyproject.toml`. Cách dùng thư viện: xem `backend/PACKAGE_README.md`.

## 1. Build tại máy

```bash
cd backend
uv build                 # hoặc: pip install build && python -m build
# -> dist/boc_tach_ban_ve-<version>-py3-none-any.whl  và  .tar.gz
```

Cài thử: `pip install dist/boc_tach_ban_ve-<version>-py3-none-any.whl`

## 2. Đẩy lên GitLab Package Registry

**Tự động (khuyên dùng):** `.gitlab-ci.yml` build và upload khi push tag.

1. Tăng `__version__` trong `backend/app/__init__.py` (registry không cho ghi đè bản cũ).
2. `git tag v0.1.1 && git push origin v0.1.1`

**Thủ công:** tạo Personal/Deploy Token có quyền `write_package_registry`, rồi

```bash
python -m twine upload \
  --repository-url https://<gitlab-host>/api/v4/projects/<PROJECT_ID>/packages/pypi \
  -u <tên-token> -p <token> backend/dist/*
```

## 3. Ứng dụng khác cài đặt

```bash
pip install boc-tach-ban-ve \
  --index-url https://<tên-token>:<token>@<gitlab-host>/api/v4/projects/<PROJECT_ID>/packages/pypi/simple
```

Hoặc trong `requirements.txt`:

```text
--extra-index-url https://<tên-token>:<token>@<gitlab-host>/api/v4/projects/<PROJECT_ID>/packages/pypi/simple
boc-tach-ban-ve==0.1.0
```

Token đọc chỉ cần quyền `read_package_registry`. Đừng commit token — dùng biến môi trường.
