import AddIcon from "@mui/icons-material/Add";
import { useNavigate } from "react-router-dom";

import ListIntegrationItem from "@components/integrations/list_integrations/ListIntegrationItem";
import NoIntegrations from "@components/integrations/list_integrations/NoIntegrations";
import { useIntegrations } from "@/contexts/IntegrationContext";
import { Button, Skeleton, Stack, Typography } from "@mui/material";

export default function ListIntegrations() {
  const navigate = useNavigate();
  const { integrations } = useIntegrations();

  return (
    <Stack spacing={8}>
      <Stack direction="row" sx={{ justifyContent: "space-between" }}>
        <Stack spacing={2} sx={{ alignItems: "start" }}>
          <Typography variant="h2">Integrations</Typography>
          <Typography variant="body2">
            Manage your existing integrations.
          </Typography>
        </Stack>
        <Stack>
          <Button
            onClick={() => navigate("add")}
            endIcon={<AddIcon />}
            variant="contained"
          >
            Create New
          </Button>
        </Stack>
      </Stack>
      {typeof integrations === "undefined" || integrations === null ? (
        <Stack spacing={8}>
          <Skeleton variant="rounded" height={75} />
        </Stack>
      ) : integrations.length > 0 ? (
        integrations.map((integration, idx) => (
          <ListIntegrationItem
            key={`${integration.type}-${idx}`}
            integrationData={integration}
          />
        ))
      ) : (
        <NoIntegrations />
      )}
    </Stack>
  );
}
