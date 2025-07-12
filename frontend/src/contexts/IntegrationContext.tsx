import React, { createContext, useContext, useEffect, useState } from "react";
import { websocketService } from "@/services/websocket";
import {
  UpdatedIntegrationParentGroupsMap,
  IntegrationResponseModel,
  ParentGroupDataResponseModel,
} from "@/types";
import api from "@/api";

interface IntegrationContextType {
  integrations: null | IntegrationResponseModel[];
  setIntegrations: React.Dispatch<
    React.SetStateAction<null | IntegrationResponseModel[]>
  >;
  parentGroups: null | Record<
    string,
    Record<string, ParentGroupDataResponseModel>
  >;
  setParentGroups: React.Dispatch<
    React.SetStateAction<Record<
      string,
      Record<string, ParentGroupDataResponseModel>
    > | null>
  >;
  currentIntegration: IntegrationResponseModel | null;
  setCurrentIntegration: React.Dispatch<
    React.SetStateAction<IntegrationResponseModel | null>
  >;
  subscribeToIntegration: (integrationId: string) => void;
  unsubscribeFromIntegration: (integrationId: string) => void;
}

const IntegrationContext = createContext<IntegrationContextType | undefined>(
  undefined,
);

export function IntegrationProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [integrations, setIntegrations] = useState<
    null | IntegrationResponseModel[]
  >(null);
  const [parentGroups, setParentGroups] = useState<Record<
    string,
    Record<string, ParentGroupDataResponseModel>
  > | null>(null);
  const [currentIntegration, setCurrentIntegration] =
    useState<IntegrationResponseModel | null>(null);
  const [subscribedIntegrations, setSubscribedIntegrations] = useState<
    Set<string>
  >(new Set());

  const fetchIntegrations = async () => {
    const resp = await api.get("/api/v1/integrations");
    const data: IntegrationResponseModel[] = resp.data;
    setIntegrations(data);
  };

  useEffect(() => {
    fetchIntegrations().catch(console.error);
  }, []);

  const updateIntegration = (
    integrationId: string,
    updatedIntegration: IntegrationResponseModel,
  ) => {
    const updatedIntegrations: IntegrationResponseModel[] = [];
    const currentIntegrations = [...(integrations || [])];
    for (const intObj of currentIntegrations) {
      if (intObj.id === integrationId) {
        updatedIntegrations.push(updatedIntegration);
      } else {
        updatedIntegrations.push(intObj);
      }
    }
    setIntegrations(updatedIntegrations);
  };

  useEffect(() => {
    // Set up WebSocket connection when there are subscribed integrations
    if (subscribedIntegrations.size > 0) {
      const handleStatusUpdate = (data: UpdatedIntegrationParentGroupsMap) => {
        Object.entries(data).forEach(([integrationId, updatedObjects]) => {
          updateIntegration(integrationId, updatedObjects.integration);
          setParentGroups((prev) => ({
            ...prev,
            [integrationId]: updatedObjects.parent_groups,
          }));
        });
      };

      // Set the Websocket's onmessage function
      websocketService.setOnMessage(handleStatusUpdate);

      // Send all subscribed integrations to Websocket
      subscribedIntegrations.forEach((integrationId) => {
        websocketService.send({ integration_id: integrationId });
      });
    }
  }, [subscribedIntegrations]);

  const subscribeToIntegration = (integrationId: string) => {
    setSubscribedIntegrations((prev) => new Set([...prev, integrationId]));
  };

  const unsubscribeFromIntegration = (integrationId: string) => {
    setSubscribedIntegrations((prev) => {
      const newSet = new Set(prev);
      newSet.delete(integrationId);
      return newSet;
    });
  };

  return (
    <IntegrationContext.Provider
      value={{
        integrations,
        setIntegrations,
        parentGroups,
        setParentGroups,
        currentIntegration,
        setCurrentIntegration,
        subscribeToIntegration,
        unsubscribeFromIntegration,
      }}
    >
      {children}
    </IntegrationContext.Provider>
  );
}

export function useIntegrations() {
  const context = useContext(IntegrationContext);
  if (context === undefined) {
    throw new Error(
      "useIntegrations must be used within an IntegrationStatusProvider",
    );
  }
  return context;
}
