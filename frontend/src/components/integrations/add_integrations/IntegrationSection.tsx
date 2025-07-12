import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Grid from "@mui/material/Grid";

import IntegrationCardButton from "@components/integrations/add_integrations/IntegrationCardButton";
import { IntegrationCardDetail } from "@/types";

type IntegrationSectionProps = {
  cardDetails: IntegrationCardDetail[];
} & React.CSSProperties;

export default function IntegrationSection({
  cardDetails,
  ...styles
}: IntegrationSectionProps) {
  return (
    <Box
      sx={{
        display: "flex",
        width: "100%",
        py: 2,
        ...styles,
      }}
    >
      <Stack
        sx={{
          alignItems: "flex-start",
        }}
        spacing={1}
      >
        <Grid container spacing={2}>
          {cardDetails.map((elt) => (
            <Grid key={elt.title} size={Math.max(12 / cardDetails.length, 3)}>
              <IntegrationCardButton
                text={elt.title}
                icon={elt.icon}
                disabled={elt.disabled}
                nav={elt.nav}
              />
            </Grid>
          ))}
        </Grid>
      </Stack>
    </Box>
  );
}
