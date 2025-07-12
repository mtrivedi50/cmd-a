import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import ExtensionIcon from "@mui/icons-material/Extension";
import IntegrationSection from "@/components/integrations/add_integrations/IntegrationSection";
import { NotionIcon, SlackIcon } from "@/components/integrations/Icons";
import GitHubIcon from "@mui/icons-material/GitHub";

export default function NoIntegrations() {
  return (
    <Stack spacing={16}>
      <Stack
        spacing={2}
        sx={{
          alignItems: "center",
          width: "100%",
        }}
      >
        <ExtensionIcon fontSize="large" />
        <Typography variant="h4">
          You don't have any integrations yet!
        </Typography>
        <Typography sx={{ color: "text.secondary" }}>
          Click "Create New" to get started today, or click on one of the
          suggested integrations below.
        </Typography>
      </Stack>
      <Stack spacing={2} sx={{ alignItems: "center" }}>
        <Typography variant="h5">Suggested:</Typography>
        <IntegrationSection
          cardDetails={[
            {
              title: "Slack",
              icon: <SlackIcon width="32" height="32" />,
              disabled: false,
              nav: "add/slack",
            },
            {
              title: "Github",
              icon: <GitHubIcon width="32" height="32" />,
              disabled: false,
              nav: "add/github",
            },
            {
              title: "Notion",
              icon: <NotionIcon width="32" height="32" />,
              disabled: false,
              nav: "add/notion",
            },
          ]}
          justifyContent="center"
        />
      </Stack>
    </Stack>
  );
}
