import {
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Typography,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import api from "@/api";
import { Chat } from "@/types";
import { useChat } from "@/contexts/ChatContext";
import { useNavigate } from "react-router-dom";

interface ChatActionMenuProps {
  chat: Chat | null;
  setClickedChat: (val: Chat | null) => void;
  anchorEl: HTMLElement | null;
  setAnchorEl: (elt: HTMLElement | null) => void;
}
export function ChatActionsMenu(props: ChatActionMenuProps) {
  const navigate = useNavigate();
  const { setAllChats, inputRef, newChatRef } = useChat();

  const handleDelete = async () => {
    props.setClickedChat(null);
    props.setAnchorEl(null);

    // Delete the integration from the database
    const deleteResponse = await api.delete(
      `/api/v1/chat/${props.chat?.chat_id}`,
    );
    if (deleteResponse.status === 200) {
      setAllChats((prev) => {
        const updatedChats: Chat[] = [];
        (prev || []).forEach((chat) => {
          if (chat.chat_id !== props.chat?.chat_id) {
            updatedChats.push(chat);
          }
        });
        return updatedChats;
      });
    }

    // Update refs
    inputRef.current = "";
    newChatRef.current = true;

    navigate("/dashboard");
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
      <MenuItem onClick={handleDelete}>
        <ListItemIcon>
          <DeleteIcon sx={{ fontSize: "1rem" }} />
        </ListItemIcon>
        <ListItemText>
          <Typography variant="body2" fontSize={"small"}>
            Delete
          </Typography>
        </ListItemText>
      </MenuItem>
    </Menu>
  );
}
