import {
  Checkbox,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  SelectChangeEvent,
  Stack,
  Typography,
} from "@mui/material";
import { IntegrationResponseModel } from "@/types";
import theme from "@/theme/theme";

import { mapIntegrationTypeToIcon } from "@/utils";
import { useEffect } from "react";

interface IntegrationsDropdownProps {
  allIntegrations: null | IntegrationResponseModel[];
  selectedChatIntegrations: null | string[];
  setSelectedChatIntegrations: (val: null | string[]) => void;
}

export function IntegrationsDropdown(props: IntegrationsDropdownProps) {
  useEffect(() => {
    if (props.selectedChatIntegrations) {
      props.setSelectedChatIntegrations(props.selectedChatIntegrations);
    }
  }, []);

  const handleChange = (event: SelectChangeEvent) => {
    props.setSelectedChatIntegrations(
      typeof event.target.value === "string"
        ? event.target.value.split(",")
        : event.target.value,
    );
  };
  return (
    <FormControl sx={{ minWidth: "17.5%", fontSize: "0.875rem" }} size="small">
      <InputLabel id="integrations-label">Integrations</InputLabel>
      <Select
        labelId="integrations-label"
        id="integrations-select"
        multiple
        value={props.selectedChatIntegrations || []}
        label="Integrations"
        autoWidth
        renderValue={(selected) => (
          <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
            <Chip
              label={
                <Typography
                  fontSize="0.75rem"
                  fontWeight="500"
                  color={theme.palette.primary.contrastText}
                >
                  {typeof selected !== "undefined" && selected.length}
                </Typography>
              }
              sx={{
                height: "1.25rem",
                borderRadius: "5px",
                fontSize: "0.875rem",
                background: theme.palette.primary.main,
              }}
            />
            <Typography fontSize="0.875rem">Selected</Typography>
          </Stack>
        )}
        // @ts-expect-error event type is not a SelectChangeEvent?
        onChange={handleChange}
      >
        {props.allIntegrations !== null &&
          props.allIntegrations.map((integration) => (
            <MenuItem key={integration.id} value={integration.id}>
              <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
                <Checkbox
                  checked={props.selectedChatIntegrations?.includes(
                    integration.id,
                  )}
                  size="small"
                />
                {mapIntegrationTypeToIcon(integration.type, "16px", "16px") ||
                  void 0}
                <Typography fontSize={"0.875rem"}>
                  {integration.name}
                </Typography>
              </Stack>
            </MenuItem>
          ))}
      </Select>
    </FormControl>
  );
}
