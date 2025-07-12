import { TextNode } from "@/types";

export interface Citation {
  citation_number: number;
  citation: TextNode;
}

export type ModelMessageKind = "request" | "response";

export interface SystemPromptPart {
  content: string;
  timestamp: string;
  dynamic_ref: string | null;
  part_kind: string;
}

export interface UserPromptPart {
  content: string;
  timestamp: string;
  part_kind: string;
}

export interface TextPart {
  content: string;
  part_kind: string;
}

export interface BaseModelMessage {
  kind: ModelMessageKind;
  chat_id: string;
  user_id: string;
}

export interface ModelRequest extends BaseModelMessage {
  context?: string;
  parts: (SystemPromptPart | UserPromptPart)[];
}

export interface ModelResponse extends BaseModelMessage {
  parts: TextPart[];
  model_name: string;
  timestamp: string;
  citations: Citation[];
}

export type ModelMessage = ModelRequest | ModelResponse;

export interface SimplifiedMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

export const partIsUserPromptPart = (
  part: SystemPromptPart | UserPromptPart,
): part is UserPromptPart => {
  return part.part_kind == "user-prompt";
};

export const modelMessageIsRequest = (
  message: ModelMessage,
): message is ModelRequest => {
  return message.kind === "request";
};

export const processPydanticRequestToUserMessage = (
  request: ModelRequest,
): SimplifiedMessage => {
  for (const part of request.parts) {
    if (partIsUserPromptPart(part)) {
      return { role: "user", content: part.content };
    }
  }
  throw new TypeError("Could not find model request!");
};

export const processPydanticResponseToAssistantMessage = (
  response: ModelResponse,
): SimplifiedMessage => {
  // We don't allow tools at the moment, so there should only be a single part that is
  // a text response...
  return {
    role: "assistant",
    content: response.parts[0].content,
    citations: response.citations,
  };
};

export const processPydanticMessageToSimplifiedMessages = (
  pydanticMessages: ModelMessage[],
): SimplifiedMessage[] => {
  const simplifiedMessages: SimplifiedMessage[] = [];
  for (const message of pydanticMessages) {
    if (modelMessageIsRequest(message)) {
      simplifiedMessages.push(processPydanticRequestToUserMessage(message));
    } else {
      simplifiedMessages.push(
        processPydanticResponseToAssistantMessage(message),
      );
    }
  }
  return simplifiedMessages;
};
