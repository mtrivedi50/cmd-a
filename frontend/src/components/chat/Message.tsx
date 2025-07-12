import { Paper } from "@mui/material";
import theme from "@/theme/theme";
import { MarkdownRenderer } from "@/components/chat/MarkdownRenderer";

interface MessageProps {
  role: "user" | "assistant";
  content: string;
}

export function Message(props: MessageProps) {
  return (
    <Paper
      elevation={0}
      sx={{
        pl: 6,
        pr: 6,
        marginBottom: 2,
        maxWidth: props.role === "user" ? "80%" : "100%",
        backgroundColor: props.role === "user" ? "#f0f0f0" : null,
        borderRadius: "10px",
        color: theme.palette.text.primary,
        alignSelf: props.role === "user" ? "flex-end" : "flex-start",
        textAlign: props.role === "user" ? "end" : "start",
      }}
    >
      <MarkdownRenderer>{props.content}</MarkdownRenderer>
    </Paper>
  );
}
