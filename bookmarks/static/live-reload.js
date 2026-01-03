const RELOAD_URL = "/live_reload";

let eventSource = null;
let serverId = null;

function connect() {
  console.debug("[live-reload] Connecting to", RELOAD_URL);

  eventSource = new EventSource(RELOAD_URL);

  eventSource.addEventListener("connected", (event) => {
    const data = JSON.parse(event.data);

    if (serverId && serverId !== data.server_id) {
      console.log("[live-reload] Server restarted, reloading page");
      window.location.reload();
      return;
    }

    console.debug("[live-reload] Connected, server ID:", data.server_id);
    serverId = data.server_id;
  });

  eventSource.addEventListener("file_change", (event) => {
    const data = JSON.parse(event.data);
    console.log("[live-reload] File changed:", data);

    if (data.file_path.endsWith(".html") || data.file_path.endsWith(".css") || data.file_path.endsWith(".js")) {
      console.log("[live-reload] Asset changed, reloading page");
      window.location.reload();
    }
  });

  eventSource.onerror = (error) => {
    console.debug("[live-reload] Disconnected", error);
    eventSource.close();
    eventSource = null;

    // Reconnect after a delay
    setTimeout(connect, 1000);
  };
}

connect();
