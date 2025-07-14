// frontend/src/components/integrations/list_integrations/EmptyParentGroups.tsx
import { Typography, Stack } from "@mui/material";
import { IntegrationType } from "@/types";
import { getParentGroupDisplayName } from "@/utils";
import ErrorIcon from "@mui/icons-material/Error";

interface NoParentGroupsErrorProps {
  type: IntegrationType;
}

export default function NoParentGroupsError(props: NoParentGroupsErrorProps) {
  const parentGroupDisplayName = getParentGroupDisplayName(props.type);
  return (
    <Stack spacing={2} sx={{ py: 8, alignItems: "center" }}>
      <ErrorIcon color="error" />
      <Typography variant="h6" color="error">
        Could not load {parentGroupDisplayName.toLowerCase()}! Try again later
        or contact support for assistance.
      </Typography>
    </Stack>
  );
}
