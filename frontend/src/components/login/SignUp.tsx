import React from "react";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";

import api, { TOKEN_DURATION } from "@/api";
import { TextFieldSpec, UserResponse } from "@/components/login/types";
import {
  validateName,
  validateUsername,
  validatePassword,
  validateSecondPassword,
} from "@/components/login/utils";
import RegistrationForm from "@/components/login/RegistrationForm";

// Styles
import "@/components/login/register.css";

// Components
export default function SignUp() {
  const [firstNameError, setFirstNameError] = React.useState(false);
  const [firstNameErrorMessage, setFirstNameErrorMessage] = React.useState("");
  const [secondNameError, setSecondNameError] = React.useState(false);
  const [secondNameErrorMessage, setSecondNameErrorMessage] =
    React.useState("");
  const [usernameError, setUsernameError] = React.useState(false);
  const [usernameErrorMessage, setUsernameErrorMessage] = React.useState("");
  const [passwordError, setPasswordError] = React.useState(false);
  const [passwordErrorMessage, setPasswordErrorMessage] = React.useState("");
  const [secondPasswordError, setSecondPasswordError] = React.useState(false);
  const [secondPasswordErrorMessage, setSecondPasswordErrorMessage] =
    React.useState("");
  const [validationErrorMessage, setValidationErrorMessage] =
    React.useState("");

  const onSuccessfulInputValidation = async (formData: {
    [key: string]: TextFieldSpec;
  }): Promise<boolean> => {
    const firstNameSpec = formData.firstName;
    const lastNameSpec = formData.lastName;
    const usernameSpec = formData.username;
    const passwordSpec = formData.password;
    const password2Spec = formData.password2;

    // For typing
    if (typeof usernameSpec.value === "undefined") {
      throw new TypeError("Username spec is missing value.");
    }
    if (typeof passwordSpec.value === "undefined") {
      throw new TypeError("Password spec is missing a value.");
    }
    if (typeof password2Spec.value === "undefined") {
      throw new TypeError("Re-entered password spec is missing a value.");
    }

    // Check if the username and password exist
    const response = await api.post("/api/v1/signup", {
      first_name: firstNameSpec.value,
      last_name: lastNameSpec.value,
      username: usernameSpec.value,
      password: passwordSpec.value,
    });
    if (response.status !== 200 && response.status !== 201) {
      setValidationErrorMessage(
        "Could not create an account with the inputted credentials. Please try again in a few minutes.",
      );
      return false;
    }
    const data: UserResponse = response.data;
    const expiration = new Date().getTime() + TOKEN_DURATION;
    localStorage.setItem("authToken", data.access_token);
    localStorage.setItem("tokenType", data.token_type);
    localStorage.setItem("tokenExpiration", expiration.toString());
    return true;
  };

  return (
    <RegistrationForm
      formWidth="500px"
      inputSpecs={[
        {
          title: "First Name",
          id: "firstName",
          type: "name",
          name: "firstName",
          placeholder: "John",
          validate: validateName,
          error: firstNameError,
          setError: setFirstNameError,
          errorMessage: firstNameErrorMessage,
          setErrorMessage: setFirstNameErrorMessage,
        },
        {
          title: "Last Name",
          id: "lastName",
          type: "name",
          name: "lastName",
          placeholder: "Smith",
          validate: validateName,
          error: secondNameError,
          setError: setSecondNameError,
          errorMessage: secondNameErrorMessage,
          setErrorMessage: setSecondNameErrorMessage,
        },
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
        {
          title: "Re-enter Password",
          id: "password2",
          type: "password",
          name: "password2",
          placeholder: "••••••",
          validate: validateSecondPassword,
          error: secondPasswordError,
          setError: setSecondPasswordError,
          errorMessage: secondPasswordErrorMessage,
          setErrorMessage: setSecondPasswordErrorMessage,
        },
      ]}
      onSuccessfulInputValidation={onSuccessfulInputValidation}
      onSuccessNavigatePath="/dashboard"
      submitButtonLabel="Create Account"
    >
      <Box
        sx={{
          display: validationErrorMessage ? "flex" : "none",
          flexDirection: "column",
          alignItems: "center",
          width: "100%",
        }}
      >
        <Typography
          sx={{
            width: "100%",
            fontSize: "1.1rem",
            fontFamily: "Inter, sans-serif",
            fontWeight: 600,
            lineHeight: 1.2,
            letterSpacing: -0.5,
            textOverflow: "wrap",
            color: "red",
          }}
        >
          {validationErrorMessage}
        </Typography>
      </Box>
      <Divider>or</Divider>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <Typography sx={{ textAlign: "center" }}>
          Already have an account?{" "}
          <Link href="/" sx={{ alignSelf: "center" }}>
            Sign in
          </Link>
        </Typography>
      </Box>
    </RegistrationForm>
  );
}
