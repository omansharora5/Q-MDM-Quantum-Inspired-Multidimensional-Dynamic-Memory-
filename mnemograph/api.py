import logging
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .auth import Credentials, DomainError
from .models import Connect, Handoff, Recall, Write, Message, Dataset, Forget, Checkpoint, Claim, ActionReceipt
from .service import MemoryService


def create_app(store, credentials: Credentials, allowed_hosts=None):
    service = MemoryService(store, credentials)
    app = FastAPI(title="Q-MDM memory service", version="0.3.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.state.service = service
    hosts = allowed_hosts or os.environ.get("MNEMO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver")
    if isinstance(hosts, str):
        hosts = [host.strip() for host in hosts.split(",") if host.strip()]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)

    @app.middleware("http")
    async def headers(request: Request, call_next):
        origin = request.headers.get("origin")
        if origin and urlsplit(origin).netloc != request.headers.get("host", request.url.netloc):
            return JSONResponse({"detail": "Cross-origin access is disabled"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        return response

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        return JSONResponse({"detail": exc.message}, status_code=exc.status)

    @app.exception_handler(Exception)
    async def server_error(request, exc):
        logging.exception("Memory operation failed")
        return JSONResponse({"detail": "Memory service is unavailable; no fallback store was selected"}, status_code=503)

    def auth(action):
        def resolve(authorization: str = Header(default="")):
            token = authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else ""
            return credentials.authorize(token, action)
        return resolve

    read, write, coordinate = auth("read"), auth("write"), auth("coordinate")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "storage": store.name, "version": "0.3.0"}

    @app.get("/api/setup")
    def setup(request: Request, scope=Depends(read)):
        return {"python":sys.executable, "workspace":str(Path(__file__).resolve().parent.parent),
                "data_directory":str(Path(store.path).resolve().parent) if hasattr(store,"path") else None,
                "url":str(request.base_url).rstrip("/"), "tenant":scope.tenant, "project":scope.project,
                "agents":credentials.agents(scope), "storage":store.name}

    @app.get("/api/state")
    def state(dataset: str | None = Query(default=None, max_length=64), scope=Depends(read)):
        return service.state(scope, dataset)

    @app.get("/api/context")
    def context(scope=Depends(read)):
        return service.context(scope)

    @app.get("/api/graph")
    def graph(dataset: str | None = Query(default=None, max_length=64), revision: int | None = Query(default=None, ge=0), scope=Depends(read)):
        return service.graph(scope, dataset, revision)

    @app.get("/api/timeline")
    def timeline(dataset: str | None = Query(default=None, max_length=64), scope=Depends(read)):
        return service.timeline(scope, dataset)

    @app.get("/api/extraction")
    def extraction(dataset: str | None = Query(default=None, max_length=64), scope=Depends(read)):
        return {"dataset": dataset, "messages": service.extraction(scope, dataset)}

    @app.get("/api/changes")
    def changes(after: int = Query(default=0, ge=0), scope=Depends(read)):
        state = service.view(scope)
        events = [event for event in state["events"] if event["revision"] > after][:200]
        return {"revision": state["revision"], "events": events, "next_cursor": events[-1]["revision"] if events else after}

    @app.post("/api/memories", status_code=201)
    def remember(command: Write, scope=Depends(write)):
        return service.save(scope, command)

    @app.put("/api/memories/{memory_id}")
    def update(memory_id: str, command: Write, scope=Depends(write)):
        return service.save(scope, command, memory_id)

    @app.get("/api/memories/{memory_id}")
    def expand(memory_id: str, version: int | None = Query(default=None, ge=1), scope=Depends(read)):
        return service.expand(scope, memory_id, version)

    @app.post("/api/recall")
    def recall(command: Recall, scope=Depends(read)):
        return service.recall(scope, command)

    @app.post("/api/connect")
    def connect(command: Connect, scope=Depends(read)):
        return service.connect(scope, command)

    @app.post("/api/handoffs", status_code=201)
    def handoff(command: Handoff, scope=Depends(coordinate)):
        return service.handoff(scope, command)

    @app.put("/api/handoffs/{task_id}")
    def update_task(task_id: str, command: Handoff, scope=Depends(coordinate)):
        return service.handoff(scope, command, task_id)

    @app.post("/api/demo")
    def demo(command: Dataset | None = None, scope=Depends(write)):
        from .demo import seed, seed_dataset
        return seed_dataset(service, scope, command.dataset) if command else seed(service, scope)

    @app.post("/api/demo/evolve")
    def evolve(command: Dataset, scope=Depends(write)):
        from .demo import evolve_dataset
        return evolve_dataset(service, scope, command.dataset)

    @app.post("/api/messages", status_code=201)
    def message(command: Message, scope=Depends(write)):
        return service.ingest_message(scope, command)

    @app.post("/api/candidates", status_code=201)
    def candidate(command: Write, scope=Depends(write)):
        command.memory.status = "asserted"
        return service.save(scope, command)

    @app.post("/api/checkpoints", status_code=201)
    def checkpoint(command: Checkpoint, scope=Depends(write)):
        return service.checkpoint(scope, command)

    @app.post("/api/handoffs/{task_id}/claim")
    def claim(task_id: str, command: Claim, scope=Depends(coordinate)):
        return service.claim(scope, task_id, command)

    @app.post("/api/actions", status_code=201)
    def ack(command: ActionReceipt, scope=Depends(coordinate)):
        return service.ack_action(scope, command)

    @app.post("/api/memories/{memory_id}/forget")
    def forget(memory_id: str, command: Forget, scope=Depends(write)):
        return service.forget(scope, memory_id, command)

    @app.get("/api/maintenance")
    def maintenance(scope=Depends(read)):
        return service.maintenance(scope)

    @app.get("/api/experiments")
    def experiments(scope=Depends(read)):
        return service.experiments()

    app.mount("/", StaticFiles(directory=Path(__file__).parent / "web", html=True), name="dashboard")
    return app
