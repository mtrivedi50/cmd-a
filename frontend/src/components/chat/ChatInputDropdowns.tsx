import { IconButton, Stack, TextField } from "@mui/material";
import { ChatModelDropdown } from "@/components/chat/ChatModelDropdown";
import { IntegrationsDropdown } from "@/components/chat/IntegrationsDropdown";
import { useChat } from "@/contexts/ChatContext";
import { useChatModel } from "@/contexts/ChatModelContext";
import { useIntegrations } from "@/contexts/IntegrationContext";
import theme from "@/theme/theme";
import SendIcon from "@mui/icons-material/Send";

interface ChatInputDropdownsProps {
  inputState: string;
  setInputState: (val: string) => void;
  handleKeyPress: (event: React.KeyboardEvent) => void;
  handleSend: React.MouseEventHandler<HTMLButtonElement> | undefined;
  isLoading: boolean;
  inputTopBorder: boolean;
}
export function ChatInputDropdowns(props: ChatInputDropdownsProps) {
  const { chatModels } = useChatModel();
  const { integrations } = useIntegrations();
  const {
    selectedChatModel,
    setSelectedChatModel,
    setSelectedChatModelName,
    setSelectedChatModelProvider,
    setSelectedChatModelSecretName,
    selectedChatIntegrations,
    setSelectedChatIntegrations,
  } = useChat();
  return (
    <Stack spacing={2}>
      <Stack sx={{ padding: 2 }} spacing={2}>
        <Stack
          direction="row"
          spacing={2}
          sx={{
            paddingTop: 2,
            alignItems: "center",
            borderTop: props.inputTopBorder
              ? `1px solid ${theme.palette.divider}`
              : null,
          }}
        >
          <TextField
            fullWidth
            multiline
            maxRows={4}
            value={props.inputState}
            onChange={(e) => props.setInputState(e.target.value)}
            onKeyDown={props.handleKeyPress}
            placeholder="Type your message..."
            variant="outlined"
            disabled={props.isLoading}
          />
          <IconButton
            color="primary"
            onClick={props.handleSend}
            sx={{ borderRadius: "25%", height: "100%", alignSelf: "flex-end" }}
          >
            <SendIcon />
          </IconButton>
        </Stack>
      </Stack>
      <div style={{ marginBottom: "1rem" }}>
        <Stack direction="row" spacing={2} sx={{ padding: 2 }}>
          <ChatModelDropdown
            allChatModels={chatModels}
            selectedChatModel={selectedChatModel}
            setSelectedChatModel={setSelectedChatModel}
            setSelectedChatModelName={setSelectedChatModelName}
            setSelectedChatModelProvider={setSelectedChatModelProvider}
            setSelectedChatModelSecretName={setSelectedChatModelSecretName}
          />
          <IntegrationsDropdown
            allIntegrations={integrations}
            selectedChatIntegrations={selectedChatIntegrations}
            setSelectedChatIntegrations={setSelectedChatIntegrations}
          />
        </Stack>
      </div>
    </Stack>
  );
}
