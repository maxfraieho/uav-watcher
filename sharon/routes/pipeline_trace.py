import os
import json
import logging
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

log = logging.getLogger(__name__)
router = APIRouter()

PROJECT_ROOT = "/home/vokov/projects/uav-watcher"

async def event_generator(job_id: str):
    trace_file = os.path.join(PROJECT_ROOT, "data", f"trace_{job_id}.jsonl")
    
    # Wait for the file to be created (up to 15 seconds)
    for _ in range(30):
        if os.path.exists(trace_file):
            break
        await asyncio.sleep(0.5)
        
    if not os.path.exists(trace_file):
        log.warning(f"[Sharon Trace] SSE trace file not found for job_id: {job_id}")
        yield f"event: error\ndata: {json.dumps({'message': 'Trace file not found'}, ensure_ascii=False)}\n\n"
        return
        
    file_pos = 0
    finished = False
    timeout_counter = 0
    max_wait_seconds = 180  # Max stream lifetime: 3 minutes
    
    log.info(f"[Sharon Trace] SSE streaming started for job_id: {job_id}")
    
    try:
        while not finished and timeout_counter < max_wait_seconds * 2:
            if not os.path.exists(trace_file):
                await asyncio.sleep(0.5)
                timeout_counter += 1
                continue
                
            with open(trace_file, "r", encoding="utf-8") as f:
                f.seek(file_pos)
                lines = f.readlines()
                file_pos = f.tell()
                
            if lines:
                timeout_counter = 0
                for line in lines:
                    if not line.strip():
                        continue
                    try:
                        event_data = json.loads(line)
                        event_type = event_data.get("event", "node_start")
                        node_name = event_data.get("node", "graph")
                        payload = event_data.get("data", {})
                        
                        log.debug(f"[Sharon Trace] SSE yield: {event_type} - {node_name}")
                        yield f"event: {event_type}\ndata: {json.dumps({'node': node_name, 'data': payload}, ensure_ascii=False)}\n\n"
                        
                        if event_type in ["done", "error"]:
                            finished = True
                            break
                    except Exception as e:
                        log.error(f"[Sharon Trace] JSON parse error in trace file: {e}")
                        yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
            else:
                await asyncio.sleep(0.5)
                timeout_counter += 1
                
        if timeout_counter >= max_wait_seconds * 2:
            log.warning(f"[Sharon Trace] SSE stream timed out for job_id: {job_id}")
            yield f"event: error\ndata: {json.dumps({'message': 'Stream timeout'}, ensure_ascii=False)}\n\n"
            
    except asyncio.CancelledError:
        log.info(f"[Sharon Trace] Client disconnected from SSE stream for job_id: {job_id}")
    except Exception as exc:
        log.error(f"[Sharon Trace] SSE streaming exception for job_id: {job_id}: {exc}")
        yield f"event: error\ndata: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"
    finally:
        log.info(f"[Sharon Trace] SSE streaming finished for job_id: {job_id}")

@router.get("/pipelines/threat/trace/{job_id}/stream")
async def get_pipeline_trace_stream(job_id: str):
    """
    Server-Sent Events (SSE) endpoint to stream threat classification graph transitions.
    For integration with the DRAKON visualizer.
    """
    return StreamingResponse(
        event_generator(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
