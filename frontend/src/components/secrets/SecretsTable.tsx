import {
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Stack,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import { SecretResponseModel } from "@/types";
import { useState } from "react";
import CreateSecret from "@/components/secrets/CreateSecret";
import { useSecret } from "@/contexts/SecretContext";
import DeleteSecret from "@/components/secrets/DeleteSecret";
import TableLoadingRow from "@/components/common/TableLoadingRow";

interface SecretColumn<
  K extends keyof SecretResponseModel = keyof SecretResponseModel,
> {
  colName: K;
  displayName: string;
  processingFunction: (val: SecretResponseModel[K]) => string | number;
}

const SecretsColumns: SecretColumn<keyof SecretResponseModel>[] = [
  {
    colName: "name",
    displayName: "Name",
    processingFunction: (val: string | number) => val,
  },
  {
    colName: "type",
    displayName: "Type",
    processingFunction: (val: string | number) => val,
  },
  {
    colName: "created_at",
    displayName: "Created At",
    processingFunction: (val: string | number) =>
      new Date(val).toLocaleString(),
  },
  {
    colName: "updated_at",
    displayName: "Updated At",
    processingFunction: (val: string | number) =>
      new Date(val).toLocaleString(),
  },
];

export function SecretsTable() {
  const [editModalOpen, setEditModalOpen] = useState<boolean>(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState<boolean>(false);
  const { secrets, setCurrentSecret } = useSecret();

  return (
    <TableContainer
      component={Paper}
      elevation={0}
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 1,
        width: "100%",
      }}
    >
      <Table>
        <TableHead>
          <TableRow>
            {SecretsColumns.map((col) => (
              <TableCell
                key={col.colName}
                sx={{
                  borderBottom: "1px solid",
                  borderColor: "divider",
                  padding: "8px",
                  fontWeight: 700,
                }}
              >
                {col.displayName}
              </TableCell>
            ))}
            <TableCell
              key="actions"
              sx={{
                borderBottom: "1px solid",
                borderColor: "divider",
                padding: "8px",
                fontWeight: 700,
              }}
            >
              Actions
            </TableCell>
          </TableRow>
        </TableHead>
        {
          <TableBody>
            {secrets === null ? (
              <TableLoadingRow nColumns={4} />
            ) : secrets.length > 0 ? (
              secrets.map((secret) => (
                <TableRow key={secret.id}>
                  {SecretsColumns.map((col) => (
                    <TableCell
                      key={col.colName}
                      sx={{
                        borderBottom: "1px solid",
                        borderColor: "divider",
                        fontSize: "0.8rem",
                      }}
                    >
                      <Typography variant="body2">
                        {col.processingFunction(secret[col.colName])}
                      </Typography>
                    </TableCell>
                  ))}
                  <TableCell
                    key="actions"
                    sx={{
                      borderBottom: "1px solid",
                      borderColor: "divider",
                      padding: "8px",
                    }}
                  >
                    <Stack direction="row" spacing={2}>
                      <EditIcon
                        fontSize="small"
                        color="primary"
                        sx={{ cursor: "pointer" }}
                        onClick={() => {
                          setEditModalOpen(true);
                          setCurrentSecret(secret);
                        }}
                      />
                      <DeleteIcon
                        fontSize="small"
                        color="primary"
                        sx={{ cursor: "pointer" }}
                        onClick={() => {
                          setDeleteModalOpen(true);
                          setCurrentSecret(secret);
                        }}
                      />
                    </Stack>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={4}>
                  <Typography variant="body2" color="text.secondary">
                    No secrets! Click "Create New +" to define your first
                    secret.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        }
      </Table>
      <CreateSecret isOpen={editModalOpen} setIsOpen={setEditModalOpen} />
      <DeleteSecret isOpen={deleteModalOpen} setIsOpen={setDeleteModalOpen} />
    </TableContainer>
  );
}
