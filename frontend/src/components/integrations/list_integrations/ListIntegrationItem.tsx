import { useEffect, useState } from "react";
import {
  Box,
  Stack,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Skeleton,
  Pagination,
  IconButton,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import {
  IntegrationResponseModel,
  IntegrationType,
  ParentGroupDataResponseModel,
} from "@/types";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import { StyledCard } from "@/theme/styledComponents";
import { SyncStatusChip } from "@/components/integrations/list_integrations/SyncStatusChip";
import { ActiveInactiveChip } from "@/components/integrations/list_integrations/ActiveInactiveChip";
import ParentGroupDetails from "@/components/integrations/list_integrations/ParentGroupDetails";
import api from "@/api";
import { useIntegrations } from "@/contexts/IntegrationContext";
import EmptyParentGroups from "@/components/integrations/list_integrations/EmptyParentGroups";
import { IntegrationActionsMenu } from "@/components/integrations/list_integrations/IntegrationActionsMenu";
import EditIntegrationModal from "@/components/integrations/forms/EditIntegrationModal";
import { mapIntegrationTypeToIcon } from "@/utils";
import NoParentGroupsError from "@/components/integrations/list_integrations/NoParentGroupsError";

interface IntegrationDetail {
  title: string;
  value: string | React.ReactNode;
}

function IntegrationIconAndType({
  integrationType,
  integrationName,
}: {
  integrationType: IntegrationType;
  integrationName: string;
}) {
  return (
    <Stack
      direction="row"
      spacing={4}
      sx={{ height: "100%", alignItems: "center", justifyContent: "start" }}
    >
      {mapIntegrationTypeToIcon(integrationType, 28, 28)}
      <Typography variant="h4">{integrationName}</Typography>
    </Stack>
  );
}

function IntegrationDetailStack({
  integrationDetail,
}: {
  integrationDetail: IntegrationDetail;
}) {
  return (
    <Stack sx={{ m: 3, minWidth: "60px" }}>
      <Box sx={{ display: "flex", alignItems: "start" }}>
        <Typography
          sx={{
            fontSize: "0.75rem",
            fontWeight: "600",
            color: "text.secondary",
          }}
        >
          {integrationDetail.title}
        </Typography>
      </Box>
      <Box sx={{ display: "flex", alignItems: "start" }}>
        {typeof integrationDetail.value === "string" ? (
          <Typography
            variant="body2"
            sx={{
              color: "primary",
            }}
          >
            {integrationDetail.value}
          </Typography>
        ) : (
          <Box sx={{ minWidth: "60px" }}>
            {" "}
            {/* Add minWidth to the value container */}
            {integrationDetail.value}
          </Box>
        )}
      </Box>
    </Stack>
  );
}

function IntegrationDetailRow({
  integrationDetails,
}: {
  integrationDetails: IntegrationDetail[];
}) {
  return (
    <Stack direction="row" spacing={12}>
      {integrationDetails.map((elt, idx) => (
        <IntegrationDetailStack key={idx} integrationDetail={elt} />
      ))}
    </Stack>
  );
}

function ParentGroupSkeletonRow() {
  return (
    <Stack direction="row" spacing={2}>
      <Box flex={1.5}>
        <Skeleton variant="text" height={48} width="100%" />
      </Box>
      <Box flex={0.75}>
        <Skeleton variant="text" height={48} width="100%" />
      </Box>
      <Box flex={1.1}>
        <Skeleton variant="text" height={48} width="100%" />
      </Box>
      <Box flex={0.5}>
        <Skeleton variant="text" height={48} width="100%" />
      </Box>
      <Box flex={0.5}>
        <Skeleton variant="text" height={48} width="100%" />
      </Box>
      <Box flex={0.5}>
        <Skeleton variant="text" height={48} width="100%" />
      </Box>
    </Stack>
  );
}

export default function ListIntegrationItem({
  integrationData,
}: {
  integrationData: IntegrationResponseModel;
}) {
  const [expanded, setExpanded] = useState(false);
  const [currentIntegrationParentGroups, setCurrentIntegrationParentGroups] =
    useState<ParentGroupDataResponseModel[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const { parentGroups, subscribeToIntegration } = useIntegrations();
  const pageSize = 5;
  const [actionsMenuAnchorElement, setActionsMenuAnchorElement] =
    useState<HTMLElement | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState<boolean>(false);

  useEffect(() => {
    subscribeToIntegration(integrationData.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [integrationData]);

  const handleAccordionChange = async (
    _event: React.SyntheticEvent,
    isExpanded: boolean,
  ) => {
    setExpanded(isExpanded);
    if (isExpanded && currentIntegrationParentGroups?.length === 0) {
      await fetchParentGroups(1);
    }
  };

  const fetchParentGroups = async (pageNumber: number) => {
    try {
      const response = await api.get(
        `/api/v1/parent-group/${integrationData.id}`,
        {
          params: {
            page: pageNumber,
            size: pageSize,
          },
        },
      );
      setCurrentIntegrationParentGroups(response.data.items);
      setTotalPages(Math.ceil(response.data.total / pageSize));
      setPage(pageNumber);
    } catch (error) {
      console.error("Error fetching parent groups:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePageChange = (
    _event: React.ChangeEvent<unknown>,
    value: number,
  ) => {
    setIsLoading(true);
    fetchParentGroups(value);
  };

  const integrationDetails = [
    {
      title: "State",
      value: <ActiveInactiveChip isActive={integrationData.is_active} />,
    },
    {
      title: "Sync Status",
      value: <SyncStatusChip status={integrationData.status} />,
    },
    {
      title: "Last Run",
      value: integrationData.last_run
        ? new Date(integrationData.last_run).toLocaleString()
        : "N/A",
    },
    { title: "Refresh Schedule", value: integrationData.refresh_schedule },
  ];

  return (
    <Stack
      direction="row"
      spacing={2}
      sx={{ alignItems: "center", width: "100%" }}
    >
      <StyledCard
        sx={{
          m: 1,
          pl: 3,
          pr: 3,
          pt: 0,
          pb: 0,
          width: "95%",
        }}
      >
        <Accordion
          expanded={expanded}
          onChange={handleAccordionChange}
          sx={{
            boxShadow: "none",
            "&:before": {
              display: "none",
            },
            "&.Mui-expanded": {
              margin: 0,
            },
            "& .MuiAccordionSummary-root": {
              "&.Mui-expanded": {
                minHeight: "48px",
              },
            },
            "& .MuiAccordionSummary-content": {
              "&.Mui-expanded": {
                margin: 0,
              },
            },
            padding: 4,
          }}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            sx={{
              px: 0,
              "&:focus": {
                outline: "none",
              },
              "& .MuiAccordionSummary-content": {
                m: 0,
              },
            }}
          >
            <Stack
              direction="row"
              sx={{ pr: 8, width: "100%", justifyContent: "space-between" }}
            >
              <div style={{ width: "40%" }}>
                <IntegrationIconAndType
                  integrationType={integrationData.type}
                  integrationName={integrationData.name}
                />
              </div>
              <div style={{ width: "60%" }}>
                <IntegrationDetailRow integrationDetails={integrationDetails} />
              </div>
            </Stack>
          </AccordionSummary>
          <AccordionDetails sx={{ px: 0 }}>
            {isLoading ? (
              <Box sx={{ p: 2, width: "100%" }}>
                <Stack spacing={2}>
                  <ParentGroupSkeletonRow />
                  <ParentGroupSkeletonRow />
                  <ParentGroupSkeletonRow />
                </Stack>
              </Box>
            ) : currentIntegrationParentGroups === null ? (
              <NoParentGroupsError type={integrationData.type} />
            ) : currentIntegrationParentGroups.length > 0 ? (
              currentIntegrationParentGroups.map((group) => (
                <Box
                  key={group.id}
                  sx={{
                    opacity: isLoading ? 0.5 : 1,
                    transition: "opacity 0.2s ease-in-out",
                  }}
                >
                  <ParentGroupDetails
                    name={group.name}
                    nodeCount={
                      parentGroups !== null &&
                      Object.keys(parentGroups).includes(integrationData.id)
                        ? parentGroups[integrationData.id][
                            group.parent_group_id
                          ].node_count
                        : group.node_count
                    }
                    edgeCount={
                      parentGroups !== null &&
                      Object.keys(parentGroups).includes(integrationData.id)
                        ? parentGroups[integrationData.id][
                            group.parent_group_id
                          ].edge_count
                        : group.edge_count
                    }
                    recordCount={
                      parentGroups !== null &&
                      Object.keys(parentGroups).includes(integrationData.id)
                        ? parentGroups[integrationData.id][
                            group.parent_group_id
                          ].record_count
                        : group.record_count
                    }
                    status={
                      parentGroups !== null &&
                      Object.keys(parentGroups).includes(integrationData.id)
                        ? parentGroups[integrationData.id][
                            group.parent_group_id
                          ].status
                        : group.status
                    }
                    lastRun={
                      parentGroups !== null &&
                      Object.keys(parentGroups).includes(integrationData.id)
                        ? parentGroups[integrationData.id][
                            group.parent_group_id
                          ].last_run
                        : group.last_run
                    }
                  />
                </Box>
              ))
            ) : (
              <EmptyParentGroups type={integrationData.type} />
            )}
            {totalPages > 1 && (
              <Box sx={{ display: "flex", justifyContent: "right", py: 2 }}>
                <Pagination
                  count={totalPages}
                  page={page}
                  onChange={handlePageChange}
                  size="small"
                  disabled={isLoading}
                  sx={{
                    "& .MuiPaginationItem-root": {
                      fontSize: "0.875rem",
                    },
                  }}
                />
              </Box>
            )}
          </AccordionDetails>
        </Accordion>
      </StyledCard>
      <IconButton
        onClick={(event: React.MouseEvent<HTMLButtonElement>) =>
          setActionsMenuAnchorElement(event.currentTarget)
        }
      >
        <MoreHorizIcon color="action" />
      </IconButton>
      <IntegrationActionsMenu
        integrationData={integrationData}
        anchorEl={actionsMenuAnchorElement}
        setAnchorEl={setActionsMenuAnchorElement}
        setIsEditModalOpen={setIsEditModalOpen}
      />
      <EditIntegrationModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        integration={integrationData}
      />
    </Stack>
  );
}
