import { Stack } from "@mui/material";
import Divider from "@mui/material/Divider";
import Typography from "@mui/material/Typography";
import GitHubIcon from "@mui/icons-material/GitHub";
import IntegrationSection from "@components/integrations/add_integrations/IntegrationSection";
import {
  SlackIcon,
  GoogleDriveIcon,
  NotionIcon,
  JiraIcon,
  ZendeskIcon,
  DropboxIcon,
} from "@components/integrations/Icons";

export default function AddIntegrations() {
  return (
    <Stack spacing={4}>
      <Stack spacing={2} sx={{ alignItems: "start" }}>
        <Typography variant="h2">Create a New Integration</Typography>
        <Typography variant="body2">
          Choose from one of the options below.
        </Typography>
      </Stack>
      <Divider sx={{ width: "100%" }} />
      <IntegrationSection
        cardDetails={[
          {
            title: "Slack",
            icon: <SlackIcon width={28} height={28} />,
            disabled: false,
            nav: "slack",
          },
          {
            title: "Github",
            icon: <GitHubIcon />,
            disabled: false,
            nav: "github",
          },
          {
            title: "Notion",
            icon: <NotionIcon width={28} height={28} />,
            disabled: true,
            nav: "slack",
          },
          {
            title: "JIRA",
            icon: <JiraIcon width={28} height={28} />,
            disabled: true,
            nav: "slack",
          },
          {
            title: "Google Drive",
            icon: <GoogleDriveIcon width={28} height={28} />,
            disabled: true,
            nav: "slack",
          },
          {
            title: "Dropbox",
            icon: <DropboxIcon width={28} height={28} />,
            disabled: true,
            nav: "slack",
          },
          {
            title: "Zendesk",
            icon: <ZendeskIcon width={28} height={28} />,
            disabled: true,
            nav: "slack",
          },
        ]}
      />
    </Stack>
  );
}
