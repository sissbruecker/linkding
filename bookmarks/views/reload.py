import json
import threading
import uuid
from pathlib import Path
from queue import Empty, Queue

from django.dispatch import receiver
from django.http import StreamingHttpResponse
from django.utils.autoreload import autoreload_started, file_changed

_styles_dir = Path(__file__).resolve().parent.parent / "styles"
_static_dir = Path(__file__).resolve().parent.parent / "static"

_server_id = str(uuid.uuid4())

_active_connections = set()
_connections_lock = threading.Lock()


def _event_stream():
    client_queue = Queue()

    with _connections_lock:
        _active_connections.add(client_queue)

    try:
        data = json.dumps({"server_id": _server_id})
        yield f"event: connected\ndata: {data}\n\n"

        while True:
            try:
                data = client_queue.get(timeout=30)
                yield f"event: file_change\ndata: {data}\n\n"
            except Empty:
                yield ": keepalive\n\n"
    finally:
        with _connections_lock:
            _active_connections.discard(client_queue)


def live_reload(request):
    response = StreamingHttpResponse(_event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    return response


@receiver(autoreload_started)
def handle_auto_reload(sender, **kwargs):
    sender.watch_dir(_styles_dir, "**/*.css")
    sender.watch_dir(_static_dir, "bundle.js")


@receiver(file_changed)
def handle_file_changed(sender, file_path, **kwargs):
    print(f"File changed: {file_path}")
    data = json.dumps({"file_path": str(file_path)})
    with _connections_lock:
        for queue in _active_connections:
            queue.put(data)

    # Return True for CSS/JS files to prevent Django server restart
    if file_path.suffix in (".css", ".js"):
        return True
