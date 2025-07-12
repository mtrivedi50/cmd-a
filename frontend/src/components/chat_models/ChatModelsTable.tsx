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
import {
  ChatModelProvider,
  ChatModelProviderLabel,
  ChatModelResponseModel,
  SecretResponseModel,
} from "@/types";
import { useState } from "react";
import CreateChatModel from "@/components/chat_models/CreateChatModel";
import DeleteChatModel from "@/components/chat_models/DeleteChatModel";
import { useChatModel } from "@/contexts/ChatModelContext";
import { chatModelProviderIcon } from "@/utils";
import TableLoadingRow from "@/components/common/TableLoadingRow";

const processProvider = (val: ChatModelProvider): React.ReactNode => {
  return (
    <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
      <div>{chatModelProviderIcon(val, "24", "24")}</div>
      <div>{ChatModelProviderLabel[val as ChatModelProvider]}</div>
    </Stack>
  );
};

interface ChatModelsTableProps {
  secrets: SecretResponseModel[];
}

interface ChatModelColumn<
  K extends keyof ChatModelResponseModel = keyof ChatModelResponseModel,
> {
  colName: K;
  displayName: string;
  processingFunction: (
    val: ChatModelResponseModel[K],
  ) => string | number | React.ReactNode;
}

const ChatModelColumns: ChatModelColumn<keyof ChatModelResponseModel>[] = [
  {
    colName: "model_name",
    displayName: "Name",
    processingFunction: (val: string | number) => val,
  },
  {
    colName: "provider",
    displayName: "Provider",
    processingFunction: (val: string | number) =>
      processProvider(val as ChatModelProvider),
  },
  {
    colName: "secret_id",
    displayName: "API Key",
    processingFunction: (_: string | number) => "**********",
  },
];

export function ChatModelsTable(props: ChatModelsTableProps) {
  const [editModalOpen, setEditModalOpen] = useState<boolean>(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState<boolean>(false);
  const { chatModels, setCurrentChatModel } = useChatModel();

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
            {ChatModelColumns.map((col) => (
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
            {chatModels === null ? (
              <TableLoadingRow nColumns={3} />
            ) : Object.keys(chatModels).length > 0 ? (
              Object.keys(chatModels).map((chatModelId) => (
                <TableRow key={chatModelId}>
                  {ChatModelColumns.map((col) => (
                    <TableCell
                      key={col.colName}
                      sx={{
                        borderBottom: "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      {col.processingFunction(
                        chatModels[chatModelId][col.colName],
                      )}
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
                          setCurrentChatModel(chatModels[chatModelId]);
                        }}
                      />
                      <DeleteIcon
                        fontSize="small"
                        color="primary"
                        sx={{ cursor: "pointer" }}
                        onClick={() => {
                          setDeleteModalOpen(true);
                          setCurrentChatModel(chatModels[chatModelId]);
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
                    No chat models! Click "Create New +" to define your first
                    chat model.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        }
        <CreateChatModel
          isOpen={editModalOpen}
          setIsOpen={setEditModalOpen}
          secrets={props.secrets}
        />
        <DeleteChatModel
          isOpen={deleteModalOpen}
          setIsOpen={setDeleteModalOpen}
        />
      </Table>
    </TableContainer>
  );
}
