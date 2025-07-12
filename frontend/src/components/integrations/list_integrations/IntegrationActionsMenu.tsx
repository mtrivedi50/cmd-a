import {
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Typography,
} from "@mui/material";
import PauseIcon from "@mui/icons-material/Pause";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import { useIntegrations } from "@/contexts/IntegrationContext";
import api from "@/api";
import { IntegrationResponseModel } from "@/types";
import { useState } from "react";
import DeleteIntegrationModal from "@/components/integrations/list_integrations/DeleteIntegrationModal";

interface IntegrationActionMenuProps {
  integrationData: IntegrationResponseModel;
  anchorEl: HTMLElement | null;
  setAnchorEl: (elt: HTMLElement | null) => void;
  setIsEditModalOpen: (val: boolean) => void;
}
export function IntegrationActionsMenu(props: IntegrationActionMenuProps) {
  const { setIntegrations } = useIntegrations();
  const [isActive, setIsActive] = useState<boolean>(
    props.integrationData.is_active,
  );
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  const handleEdit = () => {
    props.setIsEditModalOpen(true);
  };

  const handlePauseUnpause = async (is_active: boolean) => {
    setIsActive(is_active);

    // Puase the integration in the database
    const patchResponse = await api.patch(
      `/api/v1/integration/${props.integrationData.id}`,
      { is_active: is_active },
    );
    const editedIntegration = patchResponse.data;
    if (patchResponse.status === 200) {
      setIntegrations((prev) => {
        const updatedIntegrations: IntegrationResponseModel[] = [];
        (prev || []).forEach((integration) => {
          if (integration.id === props.integrationData.id) {
            updatedIntegrations.push(editedIntegration);
          } else {
            updatedIntegrations.push(integration);
          }
        });
        return updatedIntegrations;
      });
    }
  };

  return (
    <Menu
      id="actions-menu"
      anchorEl={props.anchorEl}
      open={props.anchorEl !== null}
      onClose={() => props.setAnchorEl(null)}
      MenuListProps={{
        "aria-labelledby": "basic-button",
      }}
    >
      {isActive ? (
        <MenuItem onClick={() => handlePauseUnpause(false)}>
          <ListItemIcon>
            <PauseIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>
            <Typography variant="body2">Pause</Typography>
          </ListItemText>
        </MenuItem>
      ) : (
        <MenuItem onClick={() => handlePauseUnpause(true)}>
          <ListItemIcon>
            <PlayArrowIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>
            <Typography variant="body2">Run</Typography>
          </ListItemText>
        </MenuItem>
      )}
      <MenuItem onClick={() => handleEdit()}>
        <ListItemIcon>
          <EditIcon fontSize="small" />
        </ListItemIcon>
        <ListItemText>
          <Typography variant="body2">Edit</Typography>
        </ListItemText>
      </MenuItem>
      <MenuItem onClick={() => setDeleteModalOpen(true)}>
        <ListItemIcon>
          <DeleteIcon fontSize="small" />
        </ListItemIcon>
        <ListItemText>
          <Typography variant="body2">Delete</Typography>
        </ListItemText>
      </MenuItem>
      <DeleteIntegrationModal
        modalOpen={deleteModalOpen}
        setModalOpen={setDeleteModalOpen}
        integrationId={props.integrationData.id}
        integrationName={props.integrationData.name}
      />
    </Menu>
  );
}
