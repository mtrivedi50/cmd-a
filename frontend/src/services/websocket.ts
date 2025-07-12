import { UpdatedIntegrationParentGroupsMap } from "@/types";
import { getBackendBaseUrl } from "@/utils";

class WebSocketService {
  private ws: WebSocket | null = null;

  constructor(private baseUrl: string) {
    // Instantiate Websocket connection
    const wsUrl = `${this.baseUrl.replace("http", "ws")}api/v1/ws/`;
    this.ws = new WebSocket(wsUrl);

    // Set open, close, and error functions
    this.ws.onopen = () => {
      console.log("WebSocket connected");
    };
    this.ws.onclose = () => {
      console.log("WebSocket disconnected");
    };
    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }

  setOnMessage(onMessage: (data: UpdatedIntegrationParentGroupsMap) => void) {
    if (this.ws) {
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(
            event.data,
          ) as UpdatedIntegrationParentGroupsMap;
          onMessage(data);
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
        }
      };
    }
  }

  send(data: { integration_id: string }) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

const baseUrl = await getBackendBaseUrl();
export const websocketService = new WebSocketService(baseUrl);
