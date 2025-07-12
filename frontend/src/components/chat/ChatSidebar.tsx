import {
  Stack,
  Drawer,
  Typography,
  Divider,
  Link,
  IconButton,
  Tooltip,
  Skeleton,
} from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { appBarHeight, drawerWidth } from "@/theme/theme";
import { useChat } from "@/contexts/ChatContext";
import { GRAY } from "@/theme/themePrimitives";
import AddIcon from "@mui/icons-material/Add";
import { useNavigate } from "react-router-dom";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import { ChatActionsMenu } from "@/components/chat/ChatActionsMenu";
import { useState } from "react";
import { Chat } from "@/types";

export default function ChatSidebar() {
  const navigate = useNavigate();
  const [clickedChat, setClickedChat] = useState<Chat | null>(null);
  const [actionsMenuAnchorElement, setActionsMenuAnchorElement] =
    useState<HTMLElement | null>(null);

  const { allChats } = useChat();
  return (
    <Drawer
      variant="permanent"
      anchor="left"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width: drawerWidth,
          boxSizing: "border-box",
          marginTop: appBarHeight,
          padding: 4,
          background: GRAY[50],
          borderRadius: 0,
        },
        marginTop: appBarHeight,
      }}
    >
      <Stack spacing={2} sx={{ textAlign: "left" }}>
        <Stack
          direction="row"
          sx={{ alignItems: "center", justifyContent: "space-between" }}
        >
          <Typography variant="body2" fontWeight={500}>
            Chats
          </Typography>
          <Tooltip title="New Chat">
            <IconButton
              onClick={() => navigate("/dashboard")}
              sx={{
                width: "24px",
                height: "24px",
                border: "1px solid gray",
                borderRadius: "5px",
              }}
            >
              <AddIcon sx={{ fontSize: "1rem" }} />
            </IconButton>
          </Tooltip>
        </Stack>
        <Divider />
        <nav>
          <Stack spacing={1}>
            {allChats === null ? (
              <>
                <Skeleton></Skeleton>
                <Skeleton></Skeleton>
                <Skeleton></Skeleton>
              </>
            ) : allChats.length === 0 ? (
              <Stack spacing={2}>
                <Typography variant="body2" fontWeight={500} color={GRAY[600]}>
                  Start your first conversation.
                </Typography>
                <Typography
                  variant="body2"
                  color={GRAY[600]}
                  sx={{ fontSize: "0.75rem" }}
                >
                  New chats will appear here once you begin.
                </Typography>
              </Stack>
            ) : (
              allChats.map((chat) => (
                <Link
                  component={RouterLink}
                  key={chat.chat_id}
                  to={`/dashboard/c/${chat.chat_id}`}
                  sx={{
                    paddingLeft: 2,
                    paddingRight: 2,
                    paddingTop: 1,
                    paddingBottom: 1,
                    "&:hover": { background: GRAY[100] },
                    cursor: "pointer",
                    borderRadius: "5px",
                  }}
                >
                  <Stack
                    direction="row"
                    sx={{
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <Typography variant="body2" color={GRAY[600]}>
                      {chat.title}
                    </Typography>
                    <IconButton
                      onClick={(event: React.MouseEvent<HTMLButtonElement>) => {
                        setClickedChat(chat);
                        setActionsMenuAnchorElement(event.currentTarget);
                      }}
                    >
                      <MoreHorizIcon
                        sx={{ fontSize: "1rem", color: GRAY[600] }}
                      />
                    </IconButton>
                  </Stack>
                </Link>
              ))
            )}
          </Stack>
        </nav>
        <ChatActionsMenu
          chat={clickedChat}
          setClickedChat={setClickedChat}
          anchorEl={actionsMenuAnchorElement}
          setAnchorEl={setActionsMenuAnchorElement}
        />
      </Stack>
    </Drawer>
  );
}
