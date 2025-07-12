import React, {
  createContext,
  Dispatch,
  SetStateAction,
  useContext,
  useState,
} from "react";
import { SecretResponseModel } from "@/types";

interface SecretContextType {
  secrets: SecretResponseModel[] | null;
  setSecrets: Dispatch<SetStateAction<SecretResponseModel[] | null>>;
  currentSecret: SecretResponseModel | null;
  setCurrentSecret: Dispatch<SetStateAction<SecretResponseModel | null>>;
}

const SecretContext = createContext<SecretContextType | undefined>(undefined);

export function SecretProvider({ children }: { children: React.ReactNode }) {
  const [secrets, setSecrets] = useState<SecretResponseModel[] | null>(null);
  const [currentSecret, setCurrentSecret] =
    useState<SecretResponseModel | null>(null);
  return (
    <SecretContext.Provider
      value={{
        secrets,
        setSecrets,
        currentSecret,
        setCurrentSecret,
      }}
    >
      {children}
    </SecretContext.Provider>
  );
}

export function useSecret() {
  const context = useContext(SecretContext);
  if (context === undefined) {
    throw new Error("useSecret must be used within an SecretProvider");
  }
  return context;
}
