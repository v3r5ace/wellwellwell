from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wellwellwell")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_db = subparsers.add_parser("init-db", help="Create the SQLite database if it does not exist")
    init_db.set_defaults(command="init-db")

    collect = subparsers.add_parser("collect", help="Capture one snapshot and store one reading")
    collect.add_argument("--image", help="Use a local image instead of capturing from the camera")
    collect.set_defaults(command="collect")

    serve = subparsers.add_parser("serve", help="Run the API and dashboard")
    serve.add_argument("--host", help="Override bind host")
    serve.add_argument("--port", type=int, help="Override bind port")
    serve.set_defaults(command="serve")

    collector_loop = subparsers.add_parser("collector-loop", help="Run the continuous collector loop")
    collector_loop.set_defaults(command="collector-loop")

    run = subparsers.add_parser(
        "run",
        help="Run the API and, when enabled, the built-in collector loop for Docker deployments",
    )
    run.add_argument("--host", help="Override bind host")
    run.add_argument("--port", type=int, help="Override bind port")
    run.set_defaults(command="run")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.command == "init-db":
        from .config import load_config
        from .db import initialize_database

        config = load_config()
        config.ensure_dirs()
        initialize_database(config.db_path)
        print(f"Initialized database at {config.db_path}")
        return

    if args.command == "collect":
        from .config import load_config
        from .service import collect_once, serialize_reading

        config = load_config()
        sample_image = Path(args.image).expanduser().resolve() if args.image else None
        if sample_image is not None and not sample_image.exists():
            raise SystemExit(f"Sample image not found: {sample_image}")
        reading = collect_once(config, sample_image=sample_image)
        print(json.dumps(serialize_reading(reading), indent=2))
        return

    if args.command == "serve":
        import uvicorn

        from .api import create_app
        from .config import load_config

        config = load_config()
        host = args.host or config.bind_host
        port = args.port or config.bind_port
        uvicorn.run(create_app(config), host=host, port=port)
        return

    if args.command == "collector-loop":
        from .config import load_config
        from .runtime import CollectorLoop

        config = load_config()
        loop = CollectorLoop(config)
        loop.start()
        try:
            loop.join()
        except KeyboardInterrupt:
            loop.stop()
        return

    if args.command == "run":
        import uvicorn

        from .api import create_app
        from .config import load_config
        from .runtime import CollectorLoop

        config = load_config()
        host = args.host or config.bind_host
        port = args.port or config.bind_port
        loop = CollectorLoop(config) if config.enable_collector else None

        if loop is not None:
            loop.start()

        try:
            uvicorn.run(create_app(config), host=host, port=port)
        finally:
            if loop is not None:
                loop.stop()
        return
