import { useEffect, useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Stack,
  Typography,
  Select,
  SelectChangeEvent,
  MenuItem,
  InputLabel,
  FormControl,
  FormHelperText,
  Divider,
  Link,
  ListItemIcon,
  ListItemText,
} from "@mui/material";

import api from "@/api";
import { red } from "@mui/material/colors";
import {
  ChatModelProvider,
  ChatModelProviderLabel,
  ChatModelResponseModel,
  SecretResponseModel,
} from "@/types";
import { useChatModel } from "@/contexts/ChatModelContext";
import { chatModelProviderIcon } from "@/utils";

interface CreateChatModelProps {
  isOpen: boolean;
  setIsOpen: (val: boolean) => void;
  secrets: SecretResponseModel[];
  setNewChatModelId?: (val: string) => void;
}

export default function CreateChatModel(props: CreateChatModelProps) {
  const [name, setName] = useState("");
  const [providerName, setProviderName] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { setChatModels, currentChatModel, setCurrentChatModel } =
    useChatModel();

  // Set current chat model
  useEffect(() => {
    if (currentChatModel !== null) {
      setName(currentChatModel.model_name);
      setProviderName(currentChatModel.provider);
      setApiKey(currentChatModel.secret_id);
    } else {
      setName("");
      setProviderName("");
      setApiKey("");
    }
  }, [currentChatModel]);

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError("Chat model name is required!");
      return;
    }
    if (!providerName.trim()) {
      setError("Chat model provider is required!");
      return;
    }
    if (!apiKey.trim()) {
      setError(`API key is required!`);
      return;
    }

    // If we've reached this stage, set error to None
    setError(null);

    // If the current chat model is not null, then we are editing a model. Send a
    // PATCH request. Otherwise, send a POST request.
    if (currentChatModel !== null) {
      const response = await api.patch(
        `/api/v1/chat-model/${currentChatModel.id}`,
        {
          provider: providerName,
          model_name: name,
          secret_id: apiKey,
        },
      );
      const editedChatModel = response.data;

      // Replace the existing chat model with the new one
      setChatModels((prev) => {
        (prev || {})[currentChatModel?.id] = editedChatModel;
        return prev;
      });
    } else {
      const response = await api.post("/api/v1/chat-model", {
        provider: providerName,
        model_name: name,
        secret_id: apiKey,
      });

      // Add the chat model to our state
      const newChatModel: ChatModelResponseModel = response.data;
      setChatModels((prev) => ({
        ...prev,
        [newChatModel.id]: newChatModel,
      }));

      // If `setNewChatModelId` is defined, then we want to pass the chat
      // model to the parent component.
      if (props.setNewChatModelId !== undefined) {
        props.setNewChatModelId(newChatModel.id);
      }
    }

    // Close modal
    handleClose();
  };

  const handleClose = () => {
    props.setIsOpen(false);
    setTimeout(() => setCurrentChatModel(null), 300);
  };

  return (
    <Dialog open={props.isOpen} onClose={handleClose} maxWidth="sm" fullWidth>
      <Stack spacing={4} sx={{ padding: 4 }}>
        <DialogTitle>
          <Stack spacing={2}>
            {currentChatModel !== null ? (
              <Typography variant="h3">Edit Chat Model</Typography>
            ) : (
              <Typography variant="h3">Create New Chat Model</Typography>
            )}
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Select which chat model to use when querying your documents!
            </Typography>
            <Divider />
          </Stack>
        </DialogTitle>
        <DialogContent>
          <Stack spacing={4} sx={{ paddingTop: 2 }}>
            <FormControl fullWidth>
              <InputLabel id="provider-select-label">
                Chat Model Provider
              </InputLabel>
              <Select
                labelId="provider-select-label"
                id="provider-select"
                value={providerName}
                label="Chat Model Provider"
                onChange={(event: SelectChangeEvent) =>
                  setProviderName(event.target.value as string)
                }
                sx={{
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {Object.values(ChatModelProvider).map((chatModelProvider) => {
                  return (
                    <MenuItem key={chatModelProvider} value={chatModelProvider}>
                      <Stack direction={"row"} sx={{ alignItems: "center" }}>
                        <ListItemIcon>
                          {chatModelProviderIcon(chatModelProvider, "24", "24")}
                        </ListItemIcon>
                        <ListItemText>
                          {ChatModelProviderLabel[chatModelProvider]}
                        </ListItemText>
                      </Stack>
                    </MenuItem>
                  );
                })}
              </Select>
              <FormHelperText>Provider for your chat model.</FormHelperText>
            </FormControl>
            <TextField
              fullWidth
              label="Chat Model Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="gpt-4o"
              required
              helperText="Name of your chat model."
            />
            <FormControl fullWidth>
              <InputLabel id="api-select-label">API Key</InputLabel>
              <Select
                labelId="api-select-label"
                id="api-select"
                label="API Key"
                value={apiKey}
                onChange={(event: SelectChangeEvent) =>
                  setApiKey(event.target.value as string)
                }
              >
                {props.secrets.map((secretData) => {
                  return (
                    <MenuItem key={secretData.slug} value={secretData.id}>
                      {secretData.name}
                    </MenuItem>
                  );
                })}
              </Select>
              <FormHelperText>
                Choose an existing API key. If you need a new API key, you can
                create one from your{" "}
                <Link href="/api_keys">API keys dashboard.</Link>
              </FormHelperText>
            </FormControl>
            {error && (
              <Typography
                color="error"
                variant="body2"
                sx={{
                  backgroundColor: red[50],
                  color: "error.main",
                  p: 1,
                  borderRadius: 1,
                }}
              >
                {error}
              </Typography>
            )}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button
            onClick={handleClose}
            sx={{
              textTransform: "none",
            }}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleSubmit}
            sx={{
              textTransform: "none",
            }}
          >
            Save
          </Button>
        </DialogActions>
      </Stack>
    </Dialog>
  );
}
