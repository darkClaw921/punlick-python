#!/usr/bin/env python3
import uvicorn
import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="OCR Document Processor")
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Хост для запуска сервера"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Порт для запуска сервера"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Включить автоматическую перезагрузку",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    uvicorn.run(
        "app.main:app", host=args.host, port=args.port, reload=args.reload
    )
