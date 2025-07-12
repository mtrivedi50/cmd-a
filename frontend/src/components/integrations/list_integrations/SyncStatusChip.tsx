import Chip from "@mui/material/Chip";
import { grey, green, red } from "@mui/material/colors";

import { IntegrationStatus } from "@/types";
import { ORANGE } from "@/theme/themePrimitives";

export function SyncStatusChip({ status }: { status: IntegrationStatus }) {
  const statusChipColor =
    status === IntegrationStatus.NOT_STARTED
      ? grey[100]
      : status === IntegrationStatus.QUEUED
        ? grey[300]
        : status === IntegrationStatus.RUNNING
          ? ORANGE[100]
          : status === IntegrationStatus.SUCCESS
            ? green[50]
            : red[50];

  const statusChipFontColor =
    status === IntegrationStatus.NOT_STARTED
      ? grey[600]
      : status === IntegrationStatus.QUEUED
        ? grey[600]
        : status === IntegrationStatus.RUNNING
          ? ORANGE[400]
          : status === IntegrationStatus.SUCCESS
            ? green[600]
            : red[600];

  return (
    <Chip
      label={status}
      size="small"
      variant="outlined"
      sx={{
        backgroundColor: statusChipColor,
        color: statusChipFontColor,
        fontSize: "0.75rem",
        fontWeight: 600,
        border: `1px solid ${statusChipFontColor}`,
      }}
    />
  );
}
