import React, { createContext, useContext, useEffect, useState } from "react";
import { ChatModelResponseModel } from "@/types";
import api from "@/api";

export type ChatModelsObject = { [key: string]: ChatModelResponseModel };

interface ChatModelContextType {
  chatModels: ChatModelsObject | null;
  setChatModels: React.Dispatch<React.SetStateAction<ChatModelsObject | null>>;
  currentChatModel: ChatModelResponseModel | null;
  setCurrentChatModel: React.Dispatch<
    React.SetStateAction<ChatModelResponseModel | null>
  >;
}

const ChatModelContext = createContext<ChatModelContextType | undefined>(
  undefined,
);

export function ChatModelProvider({ children }: { children: React.ReactNode }) {
  const [chatModels, setChatModels] = useState<ChatModelsObject | null>(null);
  const [currentChatModel, setCurrentChatModel] =
    useState<ChatModelResponseModel | null>(null);

  const fetchChatModels = async () => {
    const chatModalsResponse = await api.get("/api/v1/chat-models");
    const chatModelData: { [key: string]: ChatModelResponseModel } = {};
    chatModalsResponse.data.forEach(
      (chatModel: ChatModelResponseModel) =>
        (chatModelData[chatModel.id] = chatModel),
    );
    setChatModels(chatModelData);
  };

  useEffect(() => {
    fetchChatModels();
  }, []);

  return (
    <ChatModelContext.Provider
      value={{
        chatModels,
        setChatModels,
        currentChatModel,
        setCurrentChatModel,
      }}
    >
      {children}
    </ChatModelContext.Provider>
  );
}

export function useChatModel() {
  const context = useContext(ChatModelContext);
  if (context === undefined) {
    throw new Error("useChatModel must be used within an ChatModelProvider");
  }
  return context;
}
