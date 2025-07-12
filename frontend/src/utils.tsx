import { ChatModelProvider, Environment, IntegrationType } from "@/types";
import OpenAiIcon from "@/assets/openai.svg?react";
import AnthropicIcon from "@/assets/anthropic.svg?react";
import GeminiIcon from "@/assets/gemini.svg?react";
import GroqIcon from "@/assets/groq.svg?react";
import MistralIcon from "@/assets/mistral.svg?react";
import {
  JiraIcon,
  NotionIcon,
  SlackIcon,
} from "@/components/integrations/Icons";

import GitHubIcon from "@mui/icons-material/GitHub";
import { Avatar } from "@mui/material";

export const chatModelProviderIcon = (
  val: ChatModelProvider,
  width: string,
  height: string,
) => {
  switch (val) {
    case ChatModelProvider.OPENAI:
      return <OpenAiIcon width={width} height={height} />;
    case ChatModelProvider.ANTHROPIC:
      return <AnthropicIcon width={width} height={height} />;
    case ChatModelProvider.GEMINI:
      return <GeminiIcon width={width} height={height} />;
    case ChatModelProvider.MISTRAL:
      return <MistralIcon width={width} height={height} />;
    case ChatModelProvider.GROQ:
      return <GroqIcon width={width} height={height} />;
  }
};

export const mapIntegrationTypeToIcon = (
  integrationType: IntegrationType,
  width: string,
  height: string,
): React.ReactElement =>
  integrationType === IntegrationType.SLACK ? (
    <SlackIcon width={width} height={height} />
  ) : integrationType === IntegrationType.GITHUB ? (
    <GitHubIcon sx={{ width: width, height: height }} />
  ) : integrationType === IntegrationType.NOTION ? (
    <NotionIcon width={width} height={height} />
  ) : integrationType === IntegrationType.JIRA ? (
    <JiraIcon width={width} height={height} />
  ) : (
    <Avatar>{(integrationType as string).charAt(0).toUpperCase()}</Avatar>
  );

export const delay = async (timeout: number) => {
  await new Promise((f) => setTimeout(f, timeout));
};

export const getBackendBaseUrl = async () => {
  let baseURL = import.meta.env.VITE_BACKEND_BASE_URL;
  const environment: Environment | undefined = import.meta.env
    .VITE_ENVIRONMENT as Environment;
  // Dev environment — use the VITE url
  if (environment && environment === Environment.DEV) {
    return baseURL;
  }

  // Prod environment, fetch runtime configuration
  try {
    const config = await fetch("/config.json").then((res) => res.json());
    baseURL = config.BACKEND_BASE_URL.replaceAll("\\x3a", ":");
    return baseURL;
  } catch (error) {
    console.warn(`Failed to load runtime config: ${error}`);
  }
};
