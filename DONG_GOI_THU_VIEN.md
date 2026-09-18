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

## 3. Phát hành công khai lên PyPI

Job `publish-pypi` dùng Trusted Publishing: PyPI tin pipeline GitLab qua OIDC,
không cần tạo/lưu token. Cấu hình một lần trên pypi.org
(Account settings → Publishing → Add a new pending publisher → tab **GitLab**):

| Trường | Giá trị |
|---|---|
| PyPI Project Name | `boc-tach-ban-ve` |
| Namespace | `hawee-group3` |
| Project name | `Boc_Tach_Ban_Ve` |
| Top-level pipeline file path | `.gitlab-ci.yml` |
| Environment name | `pypi` |

Sau đó push tag như mục 2. Ai cũng cài được:

```bash
pip install boc-tach-ban-ve
```

## 4. Cài từ GitLab Registry (nội bộ, cần token)

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
