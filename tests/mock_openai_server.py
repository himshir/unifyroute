import asyncio
import json
from fastapi import FastAPI, Depends, Request
from fastapi.responses import StreamingResponse

app = FastAPI()

async def generate_mock_stream():
    yield "data: " + json.dumps({"id": "mock-1", "object": "chat.completion.chunk", "created": 12345, "model": "mock-model", "choices": [{"index": 0, "delta": {"role": "assistant", "content": "Hello"}, "finish_reason": None}]}) + "\n\n"
    await asyncio.sleep(0.1)
    yield "data: " + json.dumps({"id": "mock-1", "object": "chat.completion.chunk", "created": 12345, "model": "mock-model", "choices": [{"index": 0, "delta": {"content": " world!"}, "finish_reason": None}]}) + "\n\n"
    await asyncio.sleep(0.1)
    yield "data: " + json.dumps({"id": "mock-1", "object": "chat.completion.chunk", "created": 12345, "model": "mock-model", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}) + "\n\n"
    # Notice: NO usage stats in chunks. This forces the API gateway's litellm.token_counter fallback!
    yield "data: [DONE]\n\n"

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    return StreamingResponse(generate_mock_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9999)
