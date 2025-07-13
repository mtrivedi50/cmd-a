import { Chip, Link, Stack, Typography, Grid } from "@mui/material";
import { mapIntegrationTypeToIcon } from "@/utils";
import { IntegrationType } from "@/types";
import { Citation } from "@/components/chat/types";

interface CitationProps {
  citations?: Citation[];
}

export default function Citations(props: CitationProps) {
  return props.citations !== undefined && props.citations.length > 0 ? (
    <Grid container spacing={2}>
      {props.citations.map((c) => (
        <Stack
          key={c.citation_number}
          direction="row"
          spacing={2}
          sx={{ alignItems: "center" }}
        >
          <Link rel="noopener" href={c.citation.url} target="_blank">
            <Chip
              label={
                <Stack direction="row" spacing={2}>
                  <Typography variant="body2">{c.citation_number}</Typography>
                  <Stack
                    direction="row"
                    spacing={2}
                    sx={{ alignItems: "center" }}
                  >
                    {mapIntegrationTypeToIcon(
                      c.citation.source as IntegrationType,
                      "20px",
                      "20px",
                    )}
                    <Typography variant="body2">
                      {c.citation.display_name}
                    </Typography>
                  </Stack>
                </Stack>
              }
              clickable
            />
          </Link>
        </Stack>
      ))}
    </Grid>
  ) : (
    void 0
  );
}
