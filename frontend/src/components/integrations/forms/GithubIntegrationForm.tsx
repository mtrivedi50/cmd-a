import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Stack,
  Button,
  Typography,
  Link,
  SelectChangeEvent,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import AddIcon from "@mui/icons-material/Add";
import GitHubIcon from "@mui/icons-material/GitHub";
import { IntegrationResponseModel, IntegrationType, SecretType } from "@/types";
import api from "@/api";
import { useNavigate } from "react-router-dom";
import CreateSecret from "@/components/secrets/CreateSecret";
import { useSecret } from "@/contexts/SecretContext";
import { useIntegrations } from "@/contexts/IntegrationContext";

interface GithubIntegrationFormProps {
  initialData?: IntegrationResponseModel;
}

export default function GithubIntegrationForm(
  props: GithubIntegrationFormProps,
) {
  const navigate = useNavigate();
  const [createNewSecret, setCreateNewSecret] = useState(false);
  const [integrationName, setIntegrationName] = useState<string>("");
  const [githubCredentialId, setGithubCredentialId] = useState<string>("");
  const [cronSchedule, setCronSchedule] = useState<string>("*/30 * * * *");
  const [finalFormError, setFinalFormError] = useState<string>("");

  // Context
  const { secrets, setSecrets } = useSecret();
  const { setIntegrations } = useIntegrations();

  useEffect(() => {
    if (props.initialData) {
      setIntegrationName(props.initialData.name);
      setGithubCredentialId(props.initialData.secret_id);
      setCronSchedule(props.initialData.refresh_schedule);
    }
  }, [props.initialData]);

  const createIntegration = useCallback(async () => {
    if (!integrationName) {
      setFinalFormError(
        "Integration name not defined. Please re-visit and try again!",
      );
    } else if (!githubCredentialId) {
      setFinalFormError(
        "Github credential not defined. Please re-visit and try again!",
      );
    } else {
      try {
        const payload = {
          name: integrationName,
          type: IntegrationType.GITHUB,
          secret_id: githubCredentialId,
          schedule: cronSchedule,
        };
        const integrationResponse =
          props.initialData === undefined
            ? await api.post("/api/v1/integration", payload)
            : await api.patch(
                `/api/v1/integration/${props.initialData.id}`,
                payload,
              );
        if (integrationResponse.status !== 200) {
          setFinalFormError(integrationResponse.statusText);
        } else {
          setIntegrations((prev) => [
            ...(prev || []),
            integrationResponse.data,
          ]);
          navigate("/integrations");
        }
      } catch (e) {
        console.error(e);
        setFinalFormError(
          "Could not create integration! Contact support for assistance.",
        );
      }
    }
  }, [integrationName, githubCredentialId, cronSchedule, navigate]);

  const fetchSecrets = async () => {
    const secretsResponse = await api.get("/api/v1/k8s-secrets");
    setSecrets(secretsResponse.data);
  };

  useEffect(() => {
    fetchSecrets();
  }, []);

  return (
    <Stack sx={{ alignItems: "center" }}>
      <Stack
        spacing={6}
        sx={{ mb: 8, width: props.initialData === undefined ? "50%" : "70%" }}
      >
        {/* Header */}
        <Stack direction="row" spacing={1}>
          <GitHubIcon width="32" height="32" />
          <Typography variant="h3">Github</Typography>
        </Stack>

        {/* Integration name */}
        <Stack spacing={2} sx={{ alignItems: "start" }}>
          <Typography variant="body2" fontWeight="600">
            Integration Name
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Set a descriptive name for this integration.
          </Typography>
          <TextField
            fullWidth
            value={integrationName}
            onChange={(e) => setIntegrationName(e.target.value)}
            placeholder="e.g., Acme Inc. Github"
            required
          />
        </Stack>

        {/* Github credentials */}
        <Stack spacing={4} sx={{ alignItems: "start" }}>
          <Stack spacing={1} sx={{ textAlign: "left" }}>
            <Typography variant="body2" fontWeight="600">
              Github Access Token
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Create a new Github personal access token or use an existing one
              from your&nbsp;
              <Link
                href="https://github.com/settings/apps"
                target="_blank"
                rel="noopener"
                sx={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 0.5,
                }}
              >
                Github developer settings.
                <OpenInNewIcon sx={{ fontSize: 16 }} />
              </Link>
            </Typography>
          </Stack>
          <Stack spacing={2} sx={{ width: "100%", textAlign: "left" }}>
            <FormControl fullWidth>
              <InputLabel id="api-select-label">Github Access Token</InputLabel>
              <Select
                labelId="api-select-label"
                id="api-select"
                label="Github Access Token"
                value={githubCredentialId}
                onChange={(event: SelectChangeEvent) =>
                  (event.target.value as string) === "new-secret"
                    ? setCreateNewSecret(true)
                    : setGithubCredentialId(event.target.value as string)
                }
              >
                {(secrets || []).map((secretData) => {
                  return (
                    <MenuItem key={secretData.slug} value={secretData.id}>
                      {secretData.name}
                    </MenuItem>
                  );
                })}
                <MenuItem key="create-new" value="new-secret">
                  <AddIcon fontSize="small" />
                </MenuItem>
              </Select>
            </FormControl>
          </Stack>
          <CreateSecret
            isOpen={createNewSecret}
            setIsOpen={setCreateNewSecret}
            type={SecretType.GITHUB_ACCESS_TOKEN}
            setNewSecretId={setGithubCredentialId}
          />
        </Stack>
        <Stack spacing={2} sx={{ textAlign: "left" }}>
          <Typography variant="body2" fontWeight="600">
            Frequency
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Set a CRON schedule for processing new messages. Default: every 30
            minutes.
          </Typography>
          <TextField
            fullWidth
            value={cronSchedule}
            onChange={(e) => setCronSchedule(e.target.value)}
            placeholder="*/30 * * * *"
            sx={{
              "& .MuiInputBase-input": {
                fontFamily: "roboto-mono",
                fontSize: "0.8rem",
              },
            }}
          />
        </Stack>
        <Button
          variant="contained"
          onClick={createIntegration}
          disabled={!integrationName || !githubCredentialId || !cronSchedule}
        >
          Create
        </Button>
        {finalFormError !== "" && (
          <Alert severity="error">{finalFormError}</Alert>
        )}
      </Stack>
    </Stack>
  );
}
