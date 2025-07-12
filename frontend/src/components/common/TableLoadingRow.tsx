import { TableRow, TableCell, Skeleton } from "@mui/material";

export default function TableLoadingRow({ nColumns }: { nColumns: number }) {
  const tableCells = [];
  for (let i = 0; i < nColumns; i++) {
    tableCells.push(
      <TableCell
        sx={{
          borderBottom: "1px solid",
          borderColor: "divider",
          fontSize: "0.8rem",
        }}
      >
        <Skeleton variant="rounded" />
      </TableCell>,
    );
  }

  return <TableRow>{...tableCells}</TableRow>;
}
