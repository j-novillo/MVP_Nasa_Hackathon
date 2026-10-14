"""FastAPI app: JSON API plus the static calendar UI."""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from brasa import __version__
from brasa.api.routes import router
from brasa.config import FRONTEND_DIR
from brasa.services.store import DataStore


def create_app(store: DataStore | None = None) -> FastAPI:
    app = FastAPI(
        title="Brasa",
        version=__version__,
        summary="Calendario de actividad de quema a partir de hotspots MODIS y VIIRS.",
    )
    app.state.store = store if store is not None else DataStore.load_default()
    app.include_router(router, prefix="/api")

    if FRONTEND_DIR.is_dir():

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(FRONTEND_DIR / "index.html")

        @app.get("/favicon.svg")
        def favicon() -> FileResponse:
            return FileResponse(FRONTEND_DIR / "favicon.svg")

        app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
        app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
        app.mount("/vendor", StaticFiles(directory=FRONTEND_DIR / "vendor"), name="vendor")

    return app


app = create_app()


def main() -> None:
    uvicorn.run(
        app,
        host=os.environ.get("BRASA_HOST", "0.0.0.0"),
        port=int(os.environ.get("BRASA_PORT", "8000")),
    )


if __name__ == "__main__":
    main()
