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
import { useSecret } from "@/contexts/SecretContext";
import { SecretResponseModel } from "@/types";

interface DeleteSecretProps {
  isOpen: boolean;
  setIsOpen: (val: boolean) => void;
}

export default function DeleteSecret(props: DeleteSecretProps) {
  const [deleteName, setDeleteName] = useState("");
  const { setSecrets, currentSecret } = useSecret();

  const handleDelete = async () => {
    if (deleteName === currentSecret?.name) {
      api.delete(`/api/v1/k8s-secret/${currentSecret.id}`);
    }

    // Remove the secret from the state
    setSecrets((prev: SecretResponseModel[] | null) => {
      const updatedSecrets: SecretResponseModel[] = [];
      (prev || []).forEach((secret) => {
        if (secret.id !== currentSecret?.id) {
          updatedSecrets.push(secret);
        }
      });
      return updatedSecrets;
    });
    setDeleteName("");
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
            <Typography variant="h3">Delete Secret</Typography>
            <Divider />
          </Stack>
        </DialogTitle>
        <DialogContent>
          <Stack spacing={4} sx={{ paddingTop: 2 }}>
            <Typography>
              Are you sure you want to delete your secret? This action cannot be
              reversed.
            </Typography>
            <TextField
              fullWidth
              value={deleteName}
              onChange={(e) => setDeleteName(e.target.value)}
              placeholder={currentSecret?.name}
              required
              helperText="Type the name of your secret to confirm."
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={handleClose}>Cancel</Button>
          <Button
            variant="contained"
            color="error"
            onClick={handleDelete}
            disabled={deleteName !== currentSecret?.name}
          >
            Delete
          </Button>
        </DialogActions>
      </Stack>
    </Dialog>
  );
}
