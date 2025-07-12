import React from "react";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";

import api from "@/api";
import { TOKEN_DURATION } from "@/api";

import RegistrationForm from "@/components/login/RegistrationForm";
import {
  TextFieldSpec,
  ErrorUserResponse,
  UserResponse,
} from "@/components/login/types";
import { validateUsername, validatePassword } from "@/components/login/utils";

// Styles
import "@/components/login/register.css";
import { isAxiosError } from "axios";

// Components
export default function SignIn() {
  const [usernameError, setUsernameError] = React.useState(false);
  const [usernameErrorMessage, setUsernameErrorMessage] = React.useState("");
  const [passwordError, setPasswordError] = React.useState(false);
  const [passwordErrorMessage, setPasswordErrorMessage] = React.useState("");

  const onSuccessfulInputValidation = async (formData: {
    [key: string]: TextFieldSpec;
  }): Promise<boolean> => {
    const usernameSpec = formData.username;
    const passwordSpec = formData.password;

    // For typing
    if (typeof usernameSpec.value === "undefined") {
      throw new TypeError("Username spec is missing value.");
    }
    if (typeof passwordSpec.value === "undefined") {
      throw new TypeError("Password spec is missing a value.");
    }

    // Check if the username and password exist
    try {
      // User was able to successfully log in.
      const response = await api.post("/api/v1/token", {
        username: usernameSpec.value,
        password: passwordSpec.value,
      });

      // Set token
      const data: UserResponse = response.data;
      const expiration = new Date().getTime() + TOKEN_DURATION;
      localStorage.setItem("authToken", data.access_token);
      localStorage.setItem("tokenType", data.token_type);
      localStorage.setItem("tokenExpiration", expiration.toString());
      return true;
    } catch (error) {
      if (isAxiosError(error)) {
        // User was not able to log in. Parse the error data and set appropriate error
        // messages.
        const response = error.response;
        if (typeof response !== "undefined") {
          const data: ErrorUserResponse = response.data.detail;
          if (data.reason == "password") {
            setPasswordError(true);
            setPasswordErrorMessage(data.message);
          } else {
            setUsernameError(true);
            setUsernameErrorMessage(data.message);
          }
          return false;
        } else {
          // Axios errors should pretty much always have a `response` object. If
          // doesn't, log the error.
          setUsernameError(true);
          setPasswordError(true);
          setPasswordErrorMessage(
            "Could not log in! Please contact support for help.",
          );
          console.log(error);
          return false;
        }
      } else {
        // For other errors, just log the error and return false
        setUsernameError(true);
        setPasswordError(true);
        setPasswordErrorMessage(
          "Could not log in! Please contact support for help.",
        );
        console.log(error);
        return false;
      }
    }
  };

  return (
    <RegistrationForm
      formWidth="400px"
      inputSpecs={[
        {
          title: "Username",
          id: "username",
          type: "username",
          name: "username",
          placeholder: "john_snow",
          validate: validateUsername,
          error: usernameError,
          setError: setUsernameError,
          errorMessage: usernameErrorMessage,
          setErrorMessage: setUsernameErrorMessage,
        },
        {
          title: "Password",
          id: "password",
          type: "password",
          name: "password",
          placeholder: "••••••",
          validate: validatePassword,
          error: passwordError,
          setError: setPasswordError,
          errorMessage: passwordErrorMessage,
          setErrorMessage: setPasswordErrorMessage,
        },
      ]}
      onSuccessfulInputValidation={onSuccessfulInputValidation}
      onSuccessNavigatePath="/dashboard"
      submitButtonLabel="Sign In"
    >
      <Divider>or</Divider>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <Typography sx={{ textAlign: "center" }}>
          Don&apos;t have an account?{" "}
          <Link href="/signup" variant="body1" sx={{ alignSelf: "center" }}>
            Sign up
          </Link>
        </Typography>
      </Box>
    </RegistrationForm>
  );
}
