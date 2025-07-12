import { Box, Typography } from "@mui/material";
import React from "react";

export default function HeaderWithIcon({
  title,
  icon,
}: {
  title: string;
  icon: React.ReactNode;
}) {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
      }}
    >
      {icon}
      <Typography
        component="div"
        variant="h5"
        sx={{
          fontWeight: 600,
          marginLeft: "0.75rem",
        }}
      >
        {title}
      </Typography>
    </Box>
  );
}
