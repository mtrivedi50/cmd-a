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
import { useIntegrations } from "@/contexts/IntegrationContext";
import { IntegrationResponseModel } from "@/types";
import api from "@/api";

interface DeleteIntegrationProps {
  modalOpen: boolean;
  setModalOpen: (val: boolean) => void;
  integrationId: string;
  integrationName: string;
}

export default function DeleteIntegrationModal(props: DeleteIntegrationProps) {
  const [deleteName, setDeleteName] = useState("");
  const { setIntegrations } = useIntegrations();

  const handleDelete = async () => {
    // Delete the integration from the database
    const deleteResponse = await api.delete(
      `/api/v1/integration/${props.integrationId}`,
    );
    if (deleteResponse.status === 200) {
      setIntegrations((prev) => {
        const updatedIntegrations: IntegrationResponseModel[] = [];
        (prev || []).forEach((integration) => {
          if (integration.id !== props.integrationId) {
            updatedIntegrations.push(integration);
          }
        });
        return updatedIntegrations;
      });
    }
    setDeleteName("");
    handleClose();
  };

  const handleClose = () => {
    props.setModalOpen(false);
  };

  return (
    <Dialog
      open={props.modalOpen}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
    >
      <Stack spacing={2} sx={{ padding: 4 }}>
        <DialogTitle>
          <Stack spacing={2}>
            <Typography variant="h3">Delete Integration</Typography>
            <Divider />
          </Stack>
        </DialogTitle>
        <DialogContent>
          <Stack spacing={4} sx={{ paddingTop: 2 }}>
            <Typography>
              Are you sure you want to delete your integration? This action
              cannot be reversed.
            </Typography>
            <TextField
              fullWidth
              value={deleteName}
              onChange={(e) => setDeleteName(e.target.value)}
              placeholder={props.integrationName}
              required
              helperText="Type the name of your integration to confirm."
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={handleClose}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleDelete}
            disabled={deleteName !== props.integrationName}
          >
            Delete
          </Button>
        </DialogActions>
      </Stack>
    </Dialog>
  );
}
