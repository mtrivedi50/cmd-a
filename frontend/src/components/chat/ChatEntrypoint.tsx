import { useEffect, useRef, useState } from "react";
import { Alert, Stack, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";
import api from "@/api";
import { useChat } from "@/contexts/ChatContext";
import { ChatInputDropdowns } from "@/components/chat/ChatInputDropdowns";

export default function ChatEntrypoint() {
  const [inputState, setInputState] = useState("");
  const navigate = useNavigate();
  const { setAllChats, inputRef, newChatRef } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { selectedChatIntegrations, selectedChatModel } = useChat();

  // On initial load
  useEffect(() => {
    inputRef.current = "";
    newChatRef.current = true;
  }, []);

  // Chat completion
  const handleSend = async () => {
    // Update the inputRef to reflect the latest input value
    inputRef.current = inputState;

    const chatId = crypto.randomUUID();
    const chatResponse = await api.post("/api/v1/chat", {
      chat_id: chatId,
      query: inputState.trim(),
    });
    setAllChats((prev) => [chatResponse.data, ...(prev || [])]);
    navigate(`/dashboard/c/${chatId}`);
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };
  return (
    <Stack spacing={2} sx={{ height: "100%", justifyContent: "center" }}>
      <Typography variant="h3">What can I help you with today?</Typography>
      <Stack spacing={4}>
        <div ref={messagesEndRef} />
      </Stack>
      {selectedChatIntegrations !== null &&
      selectedChatIntegrations.length === 0 ? (
        <Stack sx={{ padding: 2, width: "calc(100% - 64px)" }}>
          <Alert severity={"info"} sx={{ textAlign: "start" }}>
            <Typography fontWeight={600} sx={{ display: "inline" }}>
              Heads up:{" "}
            </Typography>
            Your query will only search in the integrations you’ve selected.
            Make sure to select any relevant integrations (e.g. Slack, GitHub,
            Notion) to get complete results.
          </Alert>
        </Stack>
      ) : selectedChatModel !== null && selectedChatModel === "" ? (
        <Stack sx={{ padding: 2, width: "calc(100% - 64px)" }}>
          <Alert severity={"info"}>Create a chat model to get started!</Alert>
        </Stack>
      ) : (
        void 0
      )}
      <ChatInputDropdowns
        inputState={inputState}
        setInputState={setInputState}
        handleKeyPress={handleKeyPress}
        handleSend={handleSend}
        isLoading={false}
        inputTopBorder={false}
      />
    </Stack>
  );
}
