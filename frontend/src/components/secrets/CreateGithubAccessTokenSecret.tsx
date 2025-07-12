import { useEffect, useState } from "react";
import {
  Link,
  TextField,
  Stack,
  Typography,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormHelperText,
  SelectChangeEvent,
} from "@mui/material";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { toProperCase } from "@/components/login/utils";

enum AccountOwnerType {
  USER = "user",
  ORG = "org",
}

interface CreateGithubAccessTokenSecretProps {
  setSecretData: (val: { [key: string]: string }) => void;
}

export default function CreateGithubAccessTokenSecret(
  props: CreateGithubAccessTokenSecretProps,
) {
  const [token, setToken] = useState("");
  const [accountOwnerType, setAccountOwnerType] = useState<AccountOwnerType>(
    AccountOwnerType.USER,
  );
  const [ownerName, setOwnerName] = useState("");

  // TODO - we don't need to re-render the component when each value is changed...
  useEffect(() => {
    props.setSecretData({
      token: token,
      org_name: accountOwnerType === AccountOwnerType.ORG ? ownerName : "",
      user_name: accountOwnerType === AccountOwnerType.USER ? ownerName : "",
    });
  }, [token, ownerName]);

  return (
    <Stack spacing={4}>
      <Divider />
      <Typography variant="h5">Github Access Token</Typography>
      <Typography variant="body2" color="text.secondary">
        Create a new Github personal access token or use an existing one from
        your&nbsp;
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

      <FormControl fullWidth>
        <InputLabel id="account-owner-type-label">
          Account owner type
        </InputLabel>
        <Select
          labelId="account-owner-type-label"
          id="account-owner-type-select"
          value={accountOwnerType}
          label="AccountOwnerType"
          onChange={(event: SelectChangeEvent) => {
            setAccountOwnerType(event.target.value as AccountOwnerType);
          }}
        >
          <MenuItem value={AccountOwnerType.USER}>
            {toProperCase(AccountOwnerType.USER)}
          </MenuItem>
          <MenuItem value={AccountOwnerType.ORG}>
            {toProperCase(AccountOwnerType.ORG)}
          </MenuItem>
        </Select>
        <FormHelperText>
          Account owner associated with the Github account.
        </FormHelperText>
      </FormControl>

      <TextField
        fullWidth
        label="Owner Name"
        value={ownerName}
        onChange={(e) => {
          setOwnerName(e.target.value);
        }}
        placeholder="acmeInc"
        required
        helperText="The organization or user name associated with the Github account."
      />

      <TextField
        fullWidth
        label="Access Token"
        value={token}
        onChange={(e) => {
          setToken(e.target.value);
        }}
        placeholder="github_pat_your_token"
        required
        helperText="Find this in your Github developer settings."
        type="password"
      />
    </Stack>
  );
}
