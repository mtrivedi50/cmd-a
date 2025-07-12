import api from "@/api";
import {
  chatWebsocketService,
  ChatWebSocketService,
} from "@/services/chat_websocket";
import { Chat, ChatModelProvider } from "@/types";
import React, {
  createContext,
  RefObject,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

interface ChatContextType {
  allChats: Chat[] | null;
  setAllChats: React.Dispatch<React.SetStateAction<Chat[] | null>>;
  selectedChatModel: string | null;
  setSelectedChatModel: (val: string | null) => void;
  selectedChatModelName: string;
  setSelectedChatModelName: (val: string) => void;
  selectedChatModelProvider: ChatModelProvider;
  setSelectedChatModelProvider: (val: ChatModelProvider) => void;
  selectedChatModelSecretName: string;
  setSelectedChatModelSecretName: (val: string) => void;
  selectedChatIntegrations: null | string[];
  setSelectedChatIntegrations: (val: null | string[]) => void;
  inputRef: RefObject<string>;
  newChatRef: RefObject<boolean>;
  chatWs: ChatWebSocketService;
}
const ChatContext = createContext<ChatContextType | undefined>(undefined);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [allChats, setAllChats] = useState<Chat[] | null>(null);
  const [selectedChatModel, setSelectedChatModel] = useState<string | null>(
    null,
  );
  const [selectedChatModelName, setSelectedChatModelName] = useState("");
  const [selectedChatModelProvider, setSelectedChatModelProvider] =
    useState<ChatModelProvider>(ChatModelProvider.OPENAI);
  const [selectedChatModelSecretName, setSelectedChatModelSecretName] =
    useState("");
  const [selectedChatIntegrations, setSelectedChatIntegrations] = useState<
    null | string[]
  >(null);
  const inputRef = useRef("");
  const newChatRef = useRef(true);

  const fetchChats = async () => {
    const chatResponse = await api.get("/api/v1/chats");
    setAllChats(chatResponse.data);
  };

  useEffect(() => {
    fetchChats();
  }, []);

  const chatWs = chatWebsocketService;

  return (
    <ChatContext.Provider
      value={{
        allChats,
        setAllChats,
        selectedChatModel,
        setSelectedChatModel,
        selectedChatModelName,
        setSelectedChatModelName,
        selectedChatModelProvider,
        setSelectedChatModelProvider,
        selectedChatModelSecretName,
        setSelectedChatModelSecretName,
        selectedChatIntegrations,
        setSelectedChatIntegrations,
        inputRef,
        newChatRef,
        chatWs,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error("useChat must be used within an ChatProvider");
  }
  return context;
}
