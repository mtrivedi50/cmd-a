import { useState } from "react";
import { Link, TextField, Stack, Typography, Divider } from "@mui/material";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";

interface CreateSlackWebTokenSecretProps {
  setSecretData: (val: { [key: string]: string }) => void;
}

export default function CreateSlackWebTokenSecret(
  props: CreateSlackWebTokenSecretProps,
) {
  const [token, setToken] = useState("");

  const handleChange = (val: string) => {
    setToken(val);
    props.setSecretData({ token: val });
  };

  return (
    <Stack spacing={4}>
      <Divider />
      <Typography variant="h5">Slack Web Token</Typography>
      <Typography variant="body2" color="text.secondary">
        Create a new Slack app or use an existing one from your&nbsp;
        <Link
          href="https://api.slack.com/apps"
          target="_blank"
          rel="noopener"
          sx={{
            display: "inline-flex",
            alignItems: "center",
            gap: 0.5,
          }}
        >
          Slack Apps dashboard
          <OpenInNewIcon sx={{ fontSize: 16 }} />
        </Link>
      </Typography>
      <TextField
        fullWidth
        label="OAuth Token"
        value={token}
        onChange={(e) => handleChange(e.target.value)}
        placeholder="xoxb-your-token"
        required
        helperText="Find this in your Slack App's OAuth & Permissions page"
        type="password"
      />
    </Stack>
  );
}
