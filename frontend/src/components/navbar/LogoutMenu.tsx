import {
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Typography,
} from "@mui/material";
import LogoutIcon from "@mui/icons-material/Logout";
import PersonIcon from "@mui/icons-material/Person";
import React from "react";
import { useNavigate } from "react-router-dom";

interface LogoutMenuProps {
  userFirstName: string;
  userLastName: string;
  anchorEl: HTMLElement | null;
  setAnchorEl: React.Dispatch<React.SetStateAction<HTMLElement | null>>;
}
export default function LogoutMenu(props: LogoutMenuProps) {
  const open = Boolean(props.anchorEl);
  const navigate = useNavigate();

  const handleClose = () => {
    props.setAnchorEl(null);
  };

  const onLogout = () => {
    handleClose();

    // Remove token from localStorage
    localStorage.removeItem("authToken");
    localStorage.removeItem("tokenType");
    localStorage.removeItem("tokenExpiration");
    navigate("/");
  };

  return (
    <Menu open={open} anchorEl={props.anchorEl} onClose={handleClose}>
      <MenuItem disabled={true}>
        <ListItemIcon>
          <PersonIcon fontSize={"small"} />
        </ListItemIcon>
        <ListItemText>
          <Typography variant="body2">
            {props.userFirstName} {props.userLastName}
          </Typography>
        </ListItemText>
      </MenuItem>
      <MenuItem onClick={onLogout}>
        <ListItemIcon>
          <LogoutIcon fontSize="small" />
        </ListItemIcon>
        <ListItemText>
          <Typography fontSize={"small"}>Logout</Typography>
        </ListItemText>
      </MenuItem>
    </Menu>
  );
}
