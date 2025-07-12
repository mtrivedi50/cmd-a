import { useEffect, useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Stack,
  Typography,
  Select,
  SelectChangeEvent,
  MenuItem,
  InputLabel,
  FormControl,
  FormHelperText,
  Divider,
} from "@mui/material";

import { red } from "@mui/material/colors";
import { SecretResponseModel, SecretType } from "@/types";
import CreateSlackWebTokenSecret from "@/components/secrets/CreateSlackWebTokenSecret";
import CreateGithubAccessTokenSecret from "@/components/secrets/CreateGithubAccessTokenSecret";
import api from "@/api";
import { useSecret } from "@/contexts/SecretContext";

interface CreateSecretProps {
  isOpen: boolean;
  setIsOpen: (val: boolean) => void;
  type?: string;
  setNewSecretId?: (val: string) => void;
}

export default function CreateSecret(props: CreateSecretProps) {
  const [type, setType] = useState(props.type || "");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [secretData, setSecretData] = useState<{ [key: string]: string }>({});
  const { setSecrets, currentSecret, setCurrentSecret } = useSecret();

  // Set current secret information
  useEffect(() => {
    if (currentSecret !== null) {
      setType(currentSecret.type);
      setName(currentSecret.name);
    } else {
      setType(props.type || "");
      setName("");
    }
  }, [currentSecret, props.type]);

  const handleSubmit = async () => {
    if (!type.trim()) {
      setError("Secret type is required!");
      return;
    }
    if (!name.trim()) {
      setError("Secret name is required!");
      return;
    }

    // If we've reached this stage, set error to None
    setError(null);

    // If the current secret is not null, then we are editing a secret. Send a PATCH
    // request. Otherwise, send a POST request.
    if (currentSecret !== null) {
      const secretResponse = await api.patch(
        `/api/v1/k8s-secret/${currentSecret.id}`,
        {
          name: name,
          type: type,
          data: secretData,
        },
      );
      const editedSecret = secretResponse.data;

      // Update the secret in the state
      setSecrets((prev: SecretResponseModel[] | null) => {
        const updatedSecrets: SecretResponseModel[] = [];
        (prev || []).forEach((secret) => {
          if (secret.id !== currentSecret?.id) {
            updatedSecrets.push(secret);
          } else {
            updatedSecrets.push(editedSecret);
          }
        });
        return updatedSecrets;
      });
    } else {
      const secretResponse = await api.post("/api/v1/k8s-secret", {
        name: name,
        type: type,
        data: secretData,
      });
      const newSecret: SecretResponseModel = secretResponse.data;
      setSecrets((prev: SecretResponseModel[] | null) => [
        ...(prev || []),
        newSecret,
      ]);

      // If `setNewSecretId` is populated, then we want to pass the secret to the parent
      // component.
      if (props.setNewSecretId !== undefined) {
        props.setNewSecretId(newSecret.id);
      }
    }

    // Close modal
    handleClose();
  };

  const handleClose = () => {
    props.setIsOpen(false);
    setTimeout(() => setCurrentSecret(null), 300);
    setType("");
    setName("");
    setSecretData({});
  };

  return (
    <Dialog open={props.isOpen} onClose={handleClose} maxWidth="sm" fullWidth>
      <Stack spacing={4} sx={{ padding: 4 }}>
        <DialogTitle>
          <Stack spacing={2}>
            {currentSecret !== null ? (
              <Typography variant="h3">Edit Secret</Typography>
            ) : (
              <Typography variant="h3">Create New Secret</Typography>
            )}
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Secrets are used to connect to third-party models or apps.
            </Typography>
            <Divider />
          </Stack>
        </DialogTitle>
        <DialogContent>
          <Stack spacing={4} sx={{ paddingTop: 2 }}>
            <FormControl fullWidth>
              <InputLabel id="secret-type-label">Secret Type</InputLabel>
              <Select
                labelId="secret-type-label"
                id="secret-type"
                value={type}
                label="Secret Type"
                onChange={(event: SelectChangeEvent) =>
                  setType(event.target.value as string)
                }
              >
                {Object.values(SecretType).map((secretType) => {
                  return (
                    <MenuItem key={secretType} value={secretType}>
                      {secretType}
                    </MenuItem>
                  );
                })}
              </Select>
              <FormHelperText>Type of secret.</FormHelperText>
            </FormControl>
            <TextField
              fullWidth
              label="Secret Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Production..."
              required
              helperText="Name for your secret."
            />
            {type === SecretType.API_KEY ? (
              <Stack spacing={4}>
                <Divider />
                <Typography variant="h5">API Key</Typography>
                <TextField
                  fullWidth
                  label="API Key"
                  value={secretData["apiKey"]}
                  onChange={(e) => setSecretData({ apiKey: e.target.value })}
                  placeholder="<your_api_key>"
                  required
                  type="password"
                />
              </Stack>
            ) : type === SecretType.SLACK_WEB_TOKEN ? (
              <CreateSlackWebTokenSecret setSecretData={setSecretData} />
            ) : type === SecretType.GITHUB_ACCESS_TOKEN ? (
              <CreateGithubAccessTokenSecret setSecretData={setSecretData} />
            ) : (
              void 0
            )}
            {error && (
              <Typography
                color="error"
                variant="body2"
                sx={{
                  backgroundColor: red[50],
                  color: "error.main",
                  p: 1,
                  borderRadius: 1,
                }}
              >
                {error}
              </Typography>
            )}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button
            onClick={handleClose}
            sx={{
              textTransform: "none",
            }}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleSubmit}
            sx={{
              textTransform: "none",
            }}
          >
            Save
          </Button>
        </DialogActions>
      </Stack>
    </Dialog>
  );
}
