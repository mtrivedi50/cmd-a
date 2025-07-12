import { getBackendBaseUrl } from "@/utils";

export class ChatWebSocketService {
  private ws: WebSocket | null = null;

  constructor(private baseUrl: string) {
    // Instantiate Websocket connection
    const wsUrl = `${this.baseUrl.replace("http", "ws")}api/v1/chat-completion/`;
    this.ws = new WebSocket(wsUrl);

    // Set open, close, and error functions
    this.ws.onopen = () => {
      console.log("ChatWebSocket connected");
    };
    this.ws.onclose = () => {
      console.log("ChatWebSocket disconnected");
    };
    this.ws.onerror = (error) => {
      console.error("ChatWebSocket error:", error);
    };
  }

  // eslint-disable-next-line  @typescript-eslint/no-explicit-any
  send(data: { [key: string]: any }) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  // eslint-disable-next-line  @typescript-eslint/no-explicit-any
  setOnMessage(onMessage: (data: { [key: string]: any }) => void) {
    if (this.ws) {
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
        } catch (error) {
          console.error("Error parsing ChatWebSocket message:", error);
        }
      };
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
export const chatWebsocketService = new ChatWebSocketService(baseUrl);
