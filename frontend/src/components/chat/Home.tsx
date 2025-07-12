import { Stack } from "@mui/material";
import ChatSidebar from "@/components/chat/ChatSidebar";
import { useChat } from "@/contexts/ChatContext";
import { useChatModel } from "@/contexts/ChatModelContext";
import { useIntegrations } from "@/contexts/IntegrationContext";
import { useEffect } from "react";

export default function Home({ children }: { children: React.ReactNode }) {
  const { chatModels } = useChatModel();
  const { integrations } = useIntegrations();
  const {
    selectedChatModel,
    setSelectedChatModel,
    setSelectedChatModelName,
    setSelectedChatModelSecretName,
    selectedChatIntegrations,
    setSelectedChatIntegrations,
  } = useChat();

  // Set the chat model and integrations
  useEffect(() => {
    if (
      chatModels !== null &&
      Object.keys(chatModels).length > 0 &&
      !selectedChatModel
    ) {
      const firstChatModel = Object.values(chatModels)[0];
      setSelectedChatModel(firstChatModel.id);
      setSelectedChatModelName(firstChatModel.model_name);
      setSelectedChatModelSecretName(firstChatModel.secret_slug);
    }
    if (integrations !== null && !selectedChatIntegrations) {
      setSelectedChatIntegrations(
        integrations.map((integration) => integration.id),
      );
    }
  }, [
    chatModels,
    setSelectedChatModel,
    setSelectedChatModelName,
    setSelectedChatModelSecretName,
    integrations,
    setSelectedChatIntegrations,
  ]);

  return (
    <Stack direction="row">
      <ChatSidebar />
      <Stack
        sx={{
          height: "calc(100vh - 4rem - 64px)",
          justifyContent: "space-between",
          width: "100%",
        }}
      >
        {children}
      </Stack>
    </Stack>
  );
}
