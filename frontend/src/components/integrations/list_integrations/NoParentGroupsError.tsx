// frontend/src/components/integrations/list_integrations/EmptyParentGroups.tsx
import { Typography, Stack } from "@mui/material";
import { IntegrationType } from "@/types";
import { getParentGroupDisplayName } from "@/utils";

interface NoParentGroupsErrorProps {
  type: IntegrationType;
}

export default function NoParentGroupsError(props: NoParentGroupsErrorProps) {
  const parentGroupDisplayName = getParentGroupDisplayName(props.type);
  return (
    <Stack sx={{ py: 8 }}>
      <Typography
        variant="h6"
        sx={{
          color: "error",
        }}
      >
        Could not load integration {parentGroupDisplayName.toLowerCase()}! Try
        again later or contact support for assistance.
      </Typography>
    </Stack>
  );
}
