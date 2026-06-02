from __future__ import annotations

from pathlib import Path
from subprocess import run

ROOT = Path(__file__).resolve().parents[1]
PROTO_DIR = ROOT / "proto"
OUT_DIR = ROOT / "app" / "grpc" / "generated"
PROTO_FILE = PROTO_DIR / "task_service.proto"
PB2_GRPC = OUT_DIR / "task_service_pb2_grpc.py"


def main() -> None:
    run(
        [
            "python",
            "-m",
            "grpc_tools.protoc",
            "-I",
            str(PROTO_DIR),
            "--python_out",
            str(OUT_DIR),
            "--grpc_python_out",
            str(OUT_DIR),
            str(PROTO_FILE),
        ],
        cwd=ROOT,
        check=True,
    )
    _patch_relative_import()
    print("gRPC stubs regenerated")


def _patch_relative_import() -> None:
    content = PB2_GRPC.read_text(encoding="utf-8")
    content = content.replace(
        "import task_service_pb2 as task__service__pb2",
        "from . import task_service_pb2 as task__service__pb2",
    )
    PB2_GRPC.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
