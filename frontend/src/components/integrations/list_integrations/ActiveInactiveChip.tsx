import Chip from "@mui/material/Chip";
import CircleIcon from "@mui/icons-material/Circle";
import CloseIcon from "@mui/icons-material/Close";
import { green, red } from "@mui/material/colors";
import { GREEN, RED } from "@/theme/themePrimitives";

export function ActiveInactiveChip({ isActive }: { isActive: boolean }) {
  // Active chip
  const activeChipColor = isActive ? green[50] : red[50];

  const activeChipFontColor = isActive ? green[600] : red[600];

  // Inactive chip icon
  const activeChipIcon = isActive ? (
    <CircleIcon
      // @ts-expect-error temporary color prop until we define a theme
      color={GREEN[600]}
      sx={{ pl: 0.5, pr: 0.5, m: 0, width: "0.7rem" }}
    />
  ) : (
    <CloseIcon
      // @ts-expect-error temporary color prop until we define a theme
      color={RED[600]}
      sx={{ pl: 0.5, pr: 0.5, m: 0, width: "0.7rem" }}
    />
  );

  const activeChipBorderColor = isActive ? GREEN[400] : RED[400];

  return (
    <Chip
      icon={activeChipIcon}
      label={isActive ? "Active" : "Inactive"}
      size="small"
      variant="outlined"
      sx={{
        backgroundColor: activeChipColor,
        color: activeChipFontColor,
        fontSize: "0.7rem",
        minWidth: "40px",
        borderColor: activeChipBorderColor,
      }}
    />
  );
}
