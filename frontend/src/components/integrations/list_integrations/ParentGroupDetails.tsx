import { Box, Typography, Stack, Skeleton } from "@mui/material";
import { grey } from "@mui/material/colors";
import { IntegrationStatus } from "@/types";
import { SyncStatusChip } from "@/components/integrations/list_integrations/SyncStatusChip";
import { BRAND } from "@/theme/themePrimitives";

interface ParentGroupDetailsProps {
  name: string;
  nodeCount: number;
  edgeCount: number;
  recordCount: number;
  status: IntegrationStatus;
  lastRun: string | null;
  isLoading?: boolean;
}

function DetailItem({
  title,
  value,
}: {
  title: string;
  value: React.ReactNode;
}) {
  return (
    <Stack spacing={0.5} sx={{ alignItems: "flex-start" }}>
      <Typography
        sx={{
          fontSize: "0.75rem",
          fontWeight: "600",
          color: grey[700],
        }}
      >
        {title}
      </Typography>
      <Box>
        {typeof value === "string" ? (
          <Typography
            sx={{
              fontSize: "0.9rem",
            }}
          >
            {value}
          </Typography>
        ) : (
          value
        )}
      </Box>
    </Stack>
  );
}

export default function ParentGroupDetails({
  name,
  nodeCount,
  edgeCount,
  recordCount,
  status,
  lastRun,
  isLoading = false,
}: ParentGroupDetailsProps) {
  if (isLoading) {
    return (
      <Box sx={{ p: 2, width: "100%" }}>
        <Stack spacing={1}>
          <Skeleton variant="text" width="60%" height={24} />
          <Stack direction="row" spacing={2}>
            <Skeleton variant="text" width={100} />
            <Skeleton variant="text" width={100} />
            <Skeleton variant="text" width={100} />
          </Stack>
        </Stack>
      </Box>
    );
  }

  return (
    <Box sx={{ width: "100%" }}>
      <Stack
        direction="row"
        sx={{
          p: 2,
          width: "100%",
          "& > *": {
            flex: 1,
          },
        }}
      >
        <Box sx={{ flex: 1.5, minWidth: 0, pr: 2 }}>
          <DetailItem
            title="Name"
            value={
              <Typography
                fontWeight={600}
                sx={{
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {name}
              </Typography>
            }
          />
        </Box>
        <Box sx={{ flex: 0.75, minWidth: 0, pr: 2 }}>
          <DetailItem
            title="Status"
            value={<SyncStatusChip status={status} />}
          />
        </Box>
        <Box sx={{ flex: 1.25, minWidth: 0, pr: 2 }}>
          <DetailItem
            title="Last Run"
            value={
              <Typography
                variant="body2"
                sx={{
                  color: BRAND[700],
                }}
              >
                {lastRun ? new Date(lastRun).toLocaleString() : "N/A"}
              </Typography>
            }
          />
        </Box>
        <Box sx={{ flex: 0.5, minWidth: 0, pr: 2 }}>
          <DetailItem
            title="Nodes"
            value={
              <Typography
                sx={{
                  fontSize: "1.2rem",
                  color: BRAND[700],
                }}
              >
                {nodeCount.toLocaleString()}
              </Typography>
            }
          />
        </Box>
        <Box sx={{ flex: 0.5, minWidth: 0, pr: 2 }}>
          <DetailItem
            title="Edges"
            value={
              <Typography
                sx={{
                  fontSize: "1.2rem",
                  color: BRAND[700],
                }}
              >
                {edgeCount.toLocaleString()}
              </Typography>
            }
          />
        </Box>
        <Box sx={{ flex: 0.5, minWidth: 0 }}>
          <DetailItem
            title="Records"
            value={
              <Typography
                sx={{
                  fontSize: "1.2rem",
                  color: BRAND[700],
                }}
              >
                {recordCount.toLocaleString()}
              </Typography>
            }
          />
        </Box>
      </Stack>
    </Box>
  );
}
