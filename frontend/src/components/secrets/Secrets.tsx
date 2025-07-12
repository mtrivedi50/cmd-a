import { Button, Stack, Typography } from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import { useCallback, useEffect, useState } from "react";
import api from "@/api";
import { SecretsTable } from "@/components/secrets/SecretsTable";
import CreateSecret from "@/components/secrets/CreateSecret";
import { useSecret } from "@/contexts/SecretContext";

export function Secrets() {
  const [createModalOpen, setCreateModalOpen] = useState<boolean>(false);
  const { setSecrets, setCurrentSecret } = useSecret();

  const fetchSecrets = useCallback(async () => {
    const secretsResponse = await api.get("/api/v1/k8s-secrets");
    setSecrets(secretsResponse.data);
  }, [setSecrets]);

  useEffect(() => {
    fetchSecrets();
  }, [fetchSecrets]);

  return (
    <Stack spacing={8}>
      <CreateSecret
        type={undefined}
        isOpen={createModalOpen}
        setIsOpen={setCreateModalOpen}
      />
      <Stack direction="row" sx={{ justifyContent: "space-between" }}>
        <Stack spacing={2} sx={{ alignItems: "start" }}>
          <Typography variant="h2">API Keys</Typography>
          <Typography variant="body2">
            Manage the API keys used in your chat models and integrations.
          </Typography>
        </Stack>
        <Stack>
          <Button
            endIcon={<AddIcon />}
            onClick={() => {
              setCurrentSecret(null);
              setCreateModalOpen(true);
            }}
            variant="contained"
          >
            Create New
          </Button>
        </Stack>
      </Stack>
      <Stack>
        <SecretsTable />
      </Stack>
    </Stack>
  );
}
