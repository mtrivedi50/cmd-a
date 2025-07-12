import {
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  SelectChangeEvent,
  Stack,
  Typography,
} from "@mui/material";
import { ChatModelProvider } from "@/types";
import { chatModelProviderIcon } from "@/utils";
import { ChatModelsObject } from "@/contexts/ChatModelContext";
import { useEffect } from "react";

interface ChatModelDropdownProps {
  allChatModels: ChatModelsObject | null;
  selectedChatModel: string | null;
  setSelectedChatModel: (val: string | null) => void;
  setSelectedChatModelName: (val: string) => void;
  setSelectedChatModelProvider: (val: ChatModelProvider) => void;
  setSelectedChatModelSecretName: (val: string) => void;
}

export function ChatModelDropdown(props: ChatModelDropdownProps) {
  useEffect(() => {
    if (props.selectedChatModel && props.allChatModels) {
      props.setSelectedChatModelName(
        props.allChatModels[props.selectedChatModel].model_name,
      );
      props.setSelectedChatModelProvider(
        props.allChatModels[props.selectedChatModel].provider,
      );
      props.setSelectedChatModelSecretName(
        props.allChatModels[props.selectedChatModel].secret_slug,
      );
    }
  }, [props.selectedChatModel]);

  const handleChange = (event: SelectChangeEvent) => {
    const chatModelId = event.target.value as string;
    if (props.allChatModels !== null) {
      props.setSelectedChatModel(chatModelId);
    }
  };

  return (
    <FormControl sx={{ minWidth: "15%", fontSize: "0.875rem" }} size="small">
      <InputLabel id="chat-model-label">Chat Model</InputLabel>
      <Select
        labelId="chat-model-label"
        id="chat-model-select"
        value={props.selectedChatModel || ""}
        label="Chat Model"
        autoWidth
        onChange={handleChange}
      >
        {Object.entries(props.allChatModels || {}).map(
          ([chatModelId, chatModel]) => (
            <MenuItem key={chatModelId} value={chatModelId}>
              <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
                {chatModelProviderIcon(
                  chatModel.provider as ChatModelProvider,
                  "16",
                  "16",
                )}
                <Typography fontSize="0.875rem">
                  {chatModel.model_name}
                </Typography>
              </Stack>
            </MenuItem>
          ),
        )}
      </Select>
    </FormControl>
  );
}
