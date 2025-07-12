import { useState, useRef, useEffect } from "react";
import { Divider, Skeleton, Stack } from "@mui/material";
import { Message } from "@/components/chat/Message";
import api from "@/api";
import { useChat } from "@/contexts/ChatContext";
import { useParams } from "react-router-dom";
import { ChatInputDropdowns } from "@/components/chat/ChatInputDropdowns";
import Citations from "@/components/chat/Citations";

import {
  Citation,
  ModelMessage,
  SimplifiedMessage,
  processPydanticMessageToSimplifiedMessages,
} from "@/components/chat/types";

export default function ChatInterface() {
  const [inputState, setInputState] = useState("");
  const { id } = useParams();
  const {
    selectedChatModelName,
    selectedChatModelProvider,
    selectedChatModelSecretName,
    selectedChatIntegrations,
    inputRef,
    newChatRef,
    chatWs,
  } = useChat();

  const [chatMessages, setChatMessages] = useState<SimplifiedMessage[] | null>(
    null,
  );
  const [assistantMessage, setAssistantMessage] =
    useState<SimplifiedMessage | null>(null);
  const [assistantMessageCitations, setAssistantMessageCitations] = useState<
    Citation[] | undefined
  >(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  // Ref for user query
  const userQueryRef = useRef("");
  // Ref to accumulate the assistant's streaming response
  const assistantContentRef = useRef("");
  // Ref to accumulate the assistant's citations
  const assistantCitationsRef = useRef<Citation[]>([]);
  // Ref for idempotency
  const onMessageSet = useRef(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Set the messages
  const fetchMessages = async (id: string | undefined) => {
    if (id) {
      setChatMessages(null);
      const messagesResponse = await api.get(`/api/v1/messages/${id}`);
      const messagesData: ModelMessage[] = messagesResponse.data;
      await new Promise((f) => setTimeout(f, 500));
      setChatMessages(processPydanticMessageToSimplifiedMessages(messagesData));
    }
  };

  useEffect(() => {
    // If we have not sent a message yet and the inputRef is populated, we are starting
    // a new chat. Send the message.
    if (newChatRef.current && inputRef.current !== "") {
      const userQuery = inputRef.current.trim();
      userQueryRef.current = userQuery;
      handleSend(userQuery);
      newChatRef.current = false;
      inputRef.current = "";
    }

    // Otherwise, we are loading messages from an existing chat
    else {
      fetchMessages(id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  useEffect(() => {
    if (!onMessageSet.current) {
      chatWs.setOnMessage((data: { [key: string]: string }) => {
        // Update the assistant message object as it builds.
        if (data.type === "token") {
          if (data.content !== "done") {
            assistantContentRef.current += data.content;
            setAssistantMessage({
              role: "assistant",
              content: assistantContentRef.current,
            });
          }
        }

        // Handle citations.
        else {
          if (data.content !== "done") {
            assistantCitationsRef.current = [
              ...assistantCitationsRef.current,
              JSON.parse(data.content),
            ];
            setAssistantMessageCitations(assistantCitationsRef.current);
          }

          // When the citations are done, the stream is done.
          else {
            // First, add the final message to chatMessages
            const finalMessage: SimplifiedMessage = {
              role: "assistant",
              content: assistantContentRef.current,
              citations: assistantCitationsRef.current,
            };
            setChatMessages((prev) => [...(prev || []), finalMessage]);

            // Then clear the streaming state
            setAssistantMessageCitations(undefined);
            setAssistantMessage(null);
            setIsLoading(false);
            assistantContentRef.current = "";
            assistantCitationsRef.current = [];
          }
        }
      });
      onMessageSet.current = true;
    }
  }, [chatWs]);

  // Chat completion
  const handleSend = async (userQuery: string) => {
    if (!userQuery) return;

    // Reset the input state
    setInputState("");

    const userMessage: SimplifiedMessage = { role: "user", content: userQuery };
    setChatMessages((prev) => [...(prev || []), userMessage]);
    setIsLoading(true);

    const chatCompletionInput = {
      chat_id: id,
      chat_model_name: selectedChatModelName,
      chat_model_secret_slug: selectedChatModelSecretName,
      chat_model_provider: selectedChatModelProvider,
      query: userQuery,
      integration_ids: selectedChatIntegrations,
    };
    chatWs.send(chatCompletionInput);
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend(inputState);
    }
  };
  return (
    <>
      <Stack spacing={4}>
        {chatMessages === null && userQueryRef.current === "" ? (
          <Stack spacing={4}>
            <Stack sx={{ display: "flex", alignItems: "end" }}>
              <Skeleton variant="rounded" height={"50px"} width={"100px"} />
            </Stack>
            <Stack sx={{ display: "flex", alignItems: "flex-start" }}>
              <Skeleton variant="rounded" height={"50px"} width={"300px"} />
            </Stack>
          </Stack>
        ) : (
          (chatMessages || []).map((message, index) => (
            <Stack
              spacing={4}
              key={index}
              sx={{
                display: "flex",
                justifyContent:
                  message.role === "user" ? "flex-end" : "flex-start",
              }}
            >
              <Message role={message.role} content={message.content} />
              <Citations citations={message.citations} />
              {message.role === "assistant" && <Divider />}
            </Stack>
          ))
        )}
        {assistantMessage !== null && (
          <Stack sx={{ display: "flex", justifyContent: "flex-start" }}>
            <Message
              role={assistantMessage.role}
              content={assistantMessage.content}
            />
            <Citations citations={assistantMessageCitations} />
          </Stack>
        )}
        <div ref={messagesEndRef} />
      </Stack>
      <ChatInputDropdowns
        inputState={inputState}
        setInputState={setInputState}
        handleKeyPress={handleKeyPress}
        handleSend={() => handleSend(inputState)}
        isLoading={isLoading}
        inputTopBorder={true}
      />
    </>
  );
}
