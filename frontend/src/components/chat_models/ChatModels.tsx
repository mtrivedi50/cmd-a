import { Button, Stack, Typography } from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import { useCallback, useEffect, useState } from "react";
import { SecretResponseModel } from "@/types";
import api from "@/api";
import { ChatModelsTable } from "@/components/chat_models/ChatModelsTable";
import CreateChatModel from "@/components/chat_models/CreateChatModel";
import { useChatModel } from "@/contexts/ChatModelContext";

export function ChatModels() {
  const [secrets, setSecrets] = useState<SecretResponseModel[]>([]);
  const [createModalOpen, setCreateModalOpen] = useState<boolean>(false);
  const { setCurrentChatModel } = useChatModel();

  const fetchSecrets = useCallback(async () => {
    const secretsResponse = await api.get("/api/v1/k8s-secrets");
    setSecrets(secretsResponse.data);
  }, [setSecrets]);

  useEffect(() => {
    fetchSecrets();
  }, [fetchSecrets]);

  return (
    <Stack spacing={8}>
      <CreateChatModel
        isOpen={createModalOpen}
        setIsOpen={setCreateModalOpen}
        secrets={secrets}
      />
      <Stack direction="row" sx={{ justifyContent: "space-between" }}>
        <Stack spacing={2} sx={{ alignItems: "start" }}>
          <Typography variant="h2">Chat Models</Typography>
          <Typography variant="body2">
            Manage the chat models used to vectorize your data.
          </Typography>
        </Stack>
        <Stack>
          <Button
            endIcon={<AddIcon />}
            onClick={() => {
              setCreateModalOpen(true);
              setCurrentChatModel(null);
            }}
            variant="contained"
          >
            Create New
          </Button>
        </Stack>
      </Stack>
      <Stack>{<ChatModelsTable secrets={secrets} />}</Stack>
    </Stack>
  );
}
