import { Dialog, DialogTitle, DialogContent } from "@mui/material";
import SlackIntegrationForm from "@/components/integrations/forms/SlackIntegrationForm";
import GithubIntegrationForm from "@/components/integrations/forms/GithubIntegrationForm";
import { IntegrationType, IntegrationResponseModel } from "@/types";

interface EditIntegrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  integration: IntegrationResponseModel;
}

export default function EditIntegrationModal({
  isOpen,
  onClose,
  integration,
}: EditIntegrationModalProps) {
  return (
    <Dialog open={isOpen} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Edit {integration.name}</DialogTitle>
      <DialogContent>
        {integration.type === IntegrationType.SLACK ? (
          <SlackIntegrationForm initialData={integration} />
        ) : integration.type === IntegrationType.GITHUB ? (
          <GithubIntegrationForm initialData={integration} />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
