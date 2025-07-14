// frontend/src/components/integrations/list_integrations/EmptyParentGroups.tsx
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import InboxIcon from "@mui/icons-material/Inbox";
import { IntegrationType } from "@/types";
import {
  GithubRepositoryIcon,
  SlackChannelIcon,
} from "@/components/integrations/Icons";
import { getParentGroupDisplayName } from "@/utils";

interface EmptyParentGroupsProps {
  type: IntegrationType;
}

export default function EmptyParentGroups(props: EmptyParentGroupsProps) {
  const properCaseTitle = getParentGroupDisplayName(props.type);

  const parentGroupIcon =
    props.type === IntegrationType.SLACK ? (
      <SlackChannelIcon width="48" height="48" />
    ) : props.type === IntegrationType.GITHUB ? (
      <GithubRepositoryIcon width="48" height="48" />
    ) : (
      <InboxIcon
        sx={{
          fontSize: 48,
          color: "text.secondary",
          mb: 1,
        }}
      />
    );

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        py: 8,
        px: 2,
        textAlign: "center",
      }}
    >
      {parentGroupIcon}
      <Typography
        variant="h6"
        sx={{
          color: "text.primary",
          mb: 1,
        }}
      >
        No {properCaseTitle}
      </Typography>
      <Typography
        variant="body2"
        sx={{
          color: "text.secondary",
          maxWidth: "400px",
        }}
      >
        This integration doesn't have any {properCaseTitle.toLowerCase()} yet.{" "}
        {properCaseTitle} will appear here once the integration is queued!
      </Typography>
    </Box>
  );
}
