export interface UserInformation {
  id: string;
  username: string;
  hashed_password: string;
  first_name: string;
  last_name: string;
  namespace: string;
  is_admin: boolean;
  is_staff: boolean;
}

export enum IntegrationType {
  SLACK = "slack",
  JIRA = "jira",
  NOTION = "notion",
  GITHUB = "github",
}

export enum IntegrationStatus {
  NOT_STARTED = "not_started",
  QUEUED = "queued",
  RUNNING = "running",
  SUCCESS = "success",
  FAILED = "failed",
}

export interface UpdatedIntegrationParentGroups {
  integration: IntegrationResponseModel;
  parent_groups: Record<string, ParentGroupDataResponseModel>;
}

export type UpdatedIntegrationParentGroupsMap = Record<
  string,
  UpdatedIntegrationParentGroups
>;

export enum ChatModelProvider {
  OPENAI = "openai",
  ANTHROPIC = "anthropic",
  GEMINI = "gemini",
  GROQ = "groq",
  MISTRAL = "mistral",
}

export const ChatModelProviderLabel: {
  [key in ChatModelProvider]: string;
} = {
  [ChatModelProvider.OPENAI]: "OpenAI",
  [ChatModelProvider.ANTHROPIC]: "Anthropic",
  [ChatModelProvider.GEMINI]: "Gemini",
  [ChatModelProvider.GROQ]: "Groq",
  [ChatModelProvider.MISTRAL]: "Mistral",
};

export interface ChatModelResponseModel {
  id: string;
  created_at: string;
  provider: ChatModelProvider;
  model_name: string;
  user_id: string;
  secret_id: string;
  secret_slug: string;
}

export interface IntegrationResponseModel {
  id: string;
  name: string;
  type: IntegrationType;
  status: IntegrationStatus;
  last_run: Date | null;
  is_active: boolean;
  refresh_schedule: string;
  user_id: string;
  secret_id: string;
}

export enum ParentGroupDataType {
  SLACK_CHANNEL = "slack_channel",
  JIRA_EPIC = "jira_epic",
  NOTION_PAGE = "notion_page",
  GITHUB_REPO = "github_repository",
}

export interface ParentGroupDataResponseModel {
  id: string;
  created_at: Date;
  parent_group_id: string;
  name: string;
  type: ParentGroupDataType;
  record_count: number;
  node_count: number;
  edge_count: number;
  status: IntegrationStatus;
  last_run: string;
  integration_id: string;
}

export interface IntegrationCardDetail {
  title: string;
  icon: React.ReactNode;
  disabled: boolean;
  nav: string;
}

export enum SecretType {
  API_KEY = "API Key",
  SLACK_WEB_TOKEN = "Slack Web Token",
  GITHUB_ACCESS_TOKEN = "GitHub Access Token",
}

export const SecretTypeLabels: { [key in SecretType]: string } = {
  [SecretType.API_KEY]: "API Key",
  [SecretType.SLACK_WEB_TOKEN]: "Slack Web Token",
  [SecretType.GITHUB_ACCESS_TOKEN]: "Github Access Token",
};

export interface SecretResponseModel {
  name: string;
  type: SecretType;
  slug: string;
  namespace: string;
  created_at: string;
  updated_at: string;
  id: string;
}

export interface Chat {
  user_id: string;
  chat_id: string;
  title: string;
  query: string;
  ts: string;
}

export interface TextNode {
  id: string;
  labels: string[];
  source: string;
  ts: string;
  url: string;
  display_name: string;
  reactions: string;
}

export enum Environment {
  DEV = "dev",
  PROD = "prod",
}
