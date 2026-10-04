import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import auth_router, problems_router, submissions_router, users_router, ws_router
from services.errors import InvalidCredentialsError, InvalidTestDataError, NotFoundError
from request_limits import RequestLimits

app = FastAPI(title="PIC18F4520 Online Judge")
app.add_middleware(RequestLimits)


@app.get("/health")
def health():
    return {"status": "ok"}

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(problems_router)
app.include_router(submissions_router)
app.include_router(users_router)
app.include_router(ws_router)


@app.exception_handler(NotFoundError)
def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(InvalidTestDataError)
def handle_invalid_test_data(request: Request, exc: InvalidTestDataError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(InvalidCredentialsError)
def handle_invalid_credentials(request: Request, exc: InvalidCredentialsError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})


def main():
    import uvicorn

    uvicorn.run("main:app", reload=True)


if __name__ == "__main__":
    main()
