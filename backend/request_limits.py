from starlette.responses import JSONResponse


class RequestLimits:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        limit = 9 * 1024 * 1024 if scope["path"] == "/api/problems" else 256 * 1024
        chunks = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > limit:
                return await JSONResponse({"detail": "Request body too large"}, status_code=413)(scope, receive, send)
            chunks.append(message)
            if not message.get("more_body", False):
                break
        index = 0
        async def replay():
            nonlocal index
            if index < len(chunks):
                message = chunks[index]
                index += 1
                return message
            return await receive()
        await self.app(scope, replay, send)
