import { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Stack,
  Typography,
  Divider,
} from "@mui/material";

import api from "@/api";
import { ChatModelsObject, useChatModel } from "@/contexts/ChatModelContext";

interface DeleteChatModelProps {
  isOpen: boolean;
  setIsOpen: (val: boolean) => void;
}

export default function DeleteChatModel(props: DeleteChatModelProps) {
  const [deleteName, setDeleteName] = useState("");
  const { setChatModels, currentChatModel } = useChatModel();

  const handleDelete = async () => {
    if (deleteName === currentChatModel?.model_name) {
      api.delete(`/api/v1/chat-model/${currentChatModel.id}`);
    }

    // Remove the secret from the state
    setChatModels((prev) => {
      if (prev !== null) {
        const updatedChatModels: ChatModelsObject = {};
        Object.keys(prev).forEach((chatModelId) => {
          if (chatModelId !== currentChatModel?.id) {
            updatedChatModels[chatModelId] = prev[chatModelId];
          }
        });
        return updatedChatModels;
      } else {
        return null;
      }
    });

    // Reset
    setDeleteName("");

    // Close modal
    handleClose();
  };

  const handleClose = () => {
    props.setIsOpen(false);
  };

  return (
    <Dialog open={props.isOpen} onClose={handleClose} maxWidth="sm" fullWidth>
      <Stack spacing={2} sx={{ padding: 4 }}>
        <DialogTitle>
          <Stack spacing={2}>
            <Typography variant="h3">Delete Chat Model</Typography>
            <Divider />
          </Stack>
        </DialogTitle>
        <DialogContent>
          <Stack spacing={4} sx={{ paddingTop: 2 }}>
            <Typography>
              Are you sure you want to delete your chat model? This action
              cannot be reversed.
            </Typography>
            <TextField
              fullWidth
              value={deleteName}
              onChange={(e) => setDeleteName(e.target.value)}
              placeholder={currentChatModel?.model_name}
              required
              helperText="Type the name of your chat model to confirm."
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={handleClose}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleDelete}
            disabled={deleteName !== currentChatModel?.model_name}
          >
            Delete
          </Button>
        </DialogActions>
      </Stack>
    </Dialog>
  );
}
