import React from "react";
import { useState } from "react";
import Card from "@mui/material/Card";
import Stack from "@mui/material/Stack";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useNavigate } from "react-router-dom";

import { BRAND, GRAY } from "@/theme/themePrimitives";

export default function IntegrationCardButton({
  text,
  icon,
  disabled,
  nav,
}: {
  text: string;
  icon: React.ReactNode;
  disabled: boolean;
  nav: string;
}) {
  const [isPressed, setIsPressed] = useState(false);
  const navigate = useNavigate();

  return (
    <Card
      sx={{
        m: 1,
        px: 10,
        py: 3,
        "&:hover": {
          backgroundColor: disabled
            ? GRAY[100]
            : isPressed
              ? BRAND[100]
              : BRAND[50],
        },
        cursor: "pointer",
        backgroundColor: disabled ? GRAY[100] : "#FFFFFF",
        opacity: disabled ? 0.5 : 1,
      }}
      onMouseDown={() => setIsPressed(true)}
      onMouseUp={() => setIsPressed(false)}
      onClick={() => navigate(nav)}
    >
      <Stack sx={{ alignItems: "center", width: "100%" }} spacing={0.5}>
        <Box>{icon}</Box>
        <Box
          sx={{
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          <Typography variant="body2" fontWeight={600}>
            {text}
          </Typography>
        </Box>
      </Stack>
    </Card>
  );
}
