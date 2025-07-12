import React from "react";
import {
  AppBar,
  Stack,
  Skeleton,
  Toolbar,
  Typography,
  Link,
  ButtonBase,
} from "@mui/material";
import Avatar from "@mui/material/Avatar";

import { UserInformation } from "@/types";

import api from "@/api";
import LogoutMenu from "@/components/navbar/LogoutMenu.tsx";
import { useNavigate } from "react-router-dom";
import axios, { AxiosError } from "axios";
import theme from "@/theme/theme";

// Convert a string to a color. Used for the color representation for the Avatar.
// Taken from:
// https://mui.com/material-ui/react-avatar/?srsltid=AfmBOor2Q8mcI9rlvz3tTjF7lMXJqqsDEnIyPbbjoP06rn9s2R6NztWx
function stringToColor(string: string) {
  let hash = 0;
  let i;
  for (i = 0; i < string.length; i += 1) {
    hash = string.charCodeAt(i) + ((hash << 5) - hash);
  }

  // Define color
  let color = "#";
  for (i = 0; i < 3; i += 1) {
    const value = (hash >> (i * 8)) & 0xff;
    color += `00${value.toString(16)}`.slice(-2);
  }
  return color;
}

export function Navbar() {
  const navigate = useNavigate();
  const [anchorEl, setAnchorEl] = React.useState<HTMLElement | null>(null);
  const [userFirstName, setUserFirstName] = React.useState("");
  const [userLastName, setUserLastName] = React.useState("");
  const [username, setUsername] = React.useState("");

  // User information
  React.useEffect(() => {
    const getUserInformation = async () => {
      try {
        const resp = await api.get(`/api/v1/user/me`);
        const userData: UserInformation = resp.data;
        setUserFirstName(userData.first_name);
        setUserLastName(userData.last_name);
        setUsername(userData.username);
      } catch (e: unknown) {
        if (axios.isAxiosError(e)) {
          const axiosError = e as AxiosError;
          if (axiosError.response?.status === 401) {
            navigate("/");
          }
        }
      }
    };
    getUserInformation();
  }, [setUserFirstName, setUserLastName, setUsername, navigate]);

  return (
    <AppBar component="nav" elevation={0}>
      <Toolbar sx={{ color: "black", justifyContent: "space-between" }}>
        <Stack direction="row" spacing={4} sx={{ alignItems: "center" }}>
          <img
            src="/cmd-a-logo.png"
            style={{ width: "32px", height: "32px" }}
          ></img>
          <Typography
            variant="h3"
            fontFamily="monospace"
            sx={{ letterSpacing: "1px" }}
          >
            cmd+A
          </Typography>
        </Stack>
        <Stack direction="row" spacing={8} sx={{ alignItems: "center" }}>
          <Link
            href="/dashboard"
            sx={{
              color: theme.palette.secondary.main,
              fontWeight: 500,
              textDecoration: "none",
            }}
          >
            Home
          </Link>
          <Link
            href="/integrations"
            sx={{
              color: theme.palette.secondary.main,
              fontWeight: 500,
              textDecoration: "none",
            }}
          >
            Integrations
          </Link>
          <Link
            href="/chat_models"
            sx={{
              color: theme.palette.secondary.main,
              fontWeight: 500,
              textDecoration: "none",
            }}
          >
            Chat Models
          </Link>
          <Link
            href="/api_keys"
            sx={{
              color: theme.palette.secondary.main,
              fontWeight: 500,
              textDecoration: "none",
            }}
          >
            API keys
          </Link>
          {!username ? (
            <Skeleton variant="circular" width={36} height={36} />
          ) : (
            <>
              <ButtonBase
                sx={{
                  borderRadius: "40px",
                  "&:has(:focus-visible)": {
                    outline: "2px solid",
                    outlineOffset: "2px",
                  },
                }}
                onClick={(event: React.MouseEvent<HTMLButtonElement>) =>
                  setAnchorEl(event.currentTarget)
                }
              >
                <Avatar
                  sizes="small"
                  sx={{
                    width: 36,
                    height: 36,
                    backgroundColor: stringToColor(
                      userFirstName[0].toUpperCase() +
                        userLastName[0].toUpperCase(),
                    ),
                    fontSize: "0.875rem",
                  }}
                >
                  {userFirstName[0].toUpperCase() +
                    userLastName[0].toUpperCase()}
                </Avatar>
              </ButtonBase>
              <LogoutMenu
                userFirstName={userFirstName}
                userLastName={userLastName}
                anchorEl={anchorEl}
                setAnchorEl={setAnchorEl}
              />
            </>
          )}
        </Stack>
      </Toolbar>
    </AppBar>
  );
}
