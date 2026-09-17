"""Lệnh `boc-tach-ban-ve` (cài kèm wheel).

    boc-tach-ban-ve serve [--host 0.0.0.0] [--port 8001]
    boc-tach-ban-ve analyze ban_ve.pdf [-o ket_qua.json]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _serve(args: argparse.Namespace) -> None:
    import uvicorn

    from .main import app

    print(f"🔌 MEP Drawing Reader API → http://localhost:{args.port}  (docs: /docs)")
    uvicorn.run(app, host=args.host, port=args.port)


def _analyze(args: argparse.Namespace) -> None:
    from . import analyze_pdf

    result = analyze_pdf(args.pdf)
    text = result.model_dump_json(indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Đã ghi {args.output} — {result.stats}")
    else:
        sys.stdout.write(text + "\n")


def main(argv: list[str] | None = None) -> None:
    from . import __version__

    parser = argparse.ArgumentParser(prog="boc-tach-ban-ve", description="Bóc tách bản vẽ MEP")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_serve = sub.add_parser("serve", help="Chạy API server (kèm /mcp)")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=8001)
    p_serve.set_defaults(func=_serve)

    p_an = sub.add_parser("analyze", help="Phân tích 1 file PDF, in JSON kết quả")
    p_an.add_argument("pdf")
    p_an.add_argument("-o", "--output", help="Ghi ra file thay vì stdout")
    p_an.set_defaults(func=_analyze)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
