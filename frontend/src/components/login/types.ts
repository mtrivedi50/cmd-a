import React from "react";

export interface TextFieldSpec {
  title: string;
  id: string;
  type: string;
  name: string;
  placeholder: string;
  validate: (
    input: string,
    previousFormData?: { [key: string]: TextFieldSpec },
  ) => [boolean, string];

  error: boolean;
  setError: React.Dispatch<React.SetStateAction<boolean>>;
  errorMessage: string;
  setErrorMessage: React.Dispatch<React.SetStateAction<string>>;

  value?: string;
}

export interface UserResponse {
  access_token: string;
  token_type: string;
}

export interface ErrorUserResponse {
  reason: "username" | "password";
  message: string;
}
