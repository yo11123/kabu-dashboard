import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..execution.sandbox import execute_code

router = APIRouter()


@router.websocket("/ws/execute")
async def websocket_execute(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            code = message.get("code", "")
            timeout = message.get("timeout", 30)

            # Run execution in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, execute_code, code, timeout
            )

            # Send stdout
            if result.get("stdout"):
                await websocket.send_json({
                    "type": "stdout",
                    "data": result["stdout"],
                })

            # Send stderr
            if result.get("stderr"):
                await websocket.send_json({
                    "type": "stderr",
                    "data": result["stderr"],
                })

            # Send figures
            for fig in result.get("figures", []):
                await websocket.send_json({
                    "type": "figure",
                    "data": fig,
                })

            # Send error
            if result.get("error"):
                await websocket.send_json({
                    "type": "error",
                    "data": result["error"],
                })

            # Send completion
            await websocket.send_json({
                "type": "complete",
                "data": {
                    "execution_time_ms": result.get("execution_time_ms", 0),
                },
            })

    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass
