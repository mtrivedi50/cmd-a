import * as React from "react";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import Stack from "@mui/material/Stack";
import Card from "@mui/material/Card";
import { useNavigate } from "react-router-dom";

import { TextFieldSpec } from "@components/login/types";
import RegistrationTextField from "@components/login/RegistrationTextField";

// Styles
import "@components/login/register.css";
import { Divider } from "@mui/material";

// Components
function FormControls({ inputSpecs }: { inputSpecs: TextFieldSpec[] }) {
  return inputSpecs.map((spec) => {
    return (
      <RegistrationTextField
        key={spec.id}
        title={spec.title}
        error={spec.error}
        errorMessage={spec.errorMessage}
        id={spec.id}
        type={spec.type}
        name={spec.name}
        placeholder={spec.placeholder}
      />
    );
  });
}

export default function RegistrationForm({
  formWidth,
  inputSpecs,
  onSuccessfulInputValidation,
  onSuccessNavigatePath,
  submitButtonLabel,
  children,
}: {
  formWidth: string;
  inputSpecs: TextFieldSpec[];
  onSuccessfulInputValidation: (formData: {
    [key: string]: TextFieldSpec;
  }) => Promise<boolean>;
  onSuccessNavigatePath: string;
  submitButtonLabel: string;
  children: React.ReactNode;
}) {
  const navigate = useNavigate();

  const validateInputs = async () => {
    let isValid = true;

    // Keep track of form inputs and values in the order in which we see them so that we
    // can pass them to the `validate` function.
    const formData: { [key: string]: TextFieldSpec } = {};

    for (const spec of inputSpecs) {
      // Grab and validate data from the form
      const value = document.getElementById(spec.id) as HTMLInputElement;
      const validationResult = spec.validate(value.value, formData);
      spec.setError(validationResult[0]);
      spec.setErrorMessage(validationResult[1]);

      // The validate function returns `true` if there is an error in the field.
      if (validationResult[0]) {
        isValid = false;
      }

      // Update previous form inputs
      spec.value = value.value;
      formData[spec.id] = spec;
    }

    // Early return if basic validation fails
    if (!isValid) {
      return false;
    }

    // If we've reached this stage, then all of the inputs are valid. Run the additional
    // validation.
    const additionalValidationPassed =
      await onSuccessfulInputValidation(formData);
    return additionalValidationPassed;
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const isValid = await validateInputs();
    if (isValid) {
      // Proceed with form submission logic
      navigate(onSuccessNavigatePath);
    } else {
      // Validation errors are already set in validateInputs
      console.log("Validation failed.");
    }
  };

  return (
    <Stack
      sx={{
        width: "100%",
        minHeight: "100%",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <Stack
        direction="column"
        justifyContent="space-between"
        className="register-form-stack"
        sx={{
          width: formWidth,
        }}
      >
        <Card className="register-form-card" variant="outlined">
          <Stack
            direction="row"
            spacing={4}
            sx={{ alignItems: "center", justifyContent: "center" }}
          >
            <img
              src="/cmd-a-logo.png"
              style={{ width: "64px", height: "64px" }}
            ></img>
            <Typography
              fontSize={"3rem"}
              fontWeight={700}
              fontFamily={"monospace"}
            >
              cmd+A
            </Typography>
          </Stack>
          <Divider />
          <Stack
            component="form"
            onSubmit={handleSubmit}
            noValidate
            spacing={4}
          >
            <FormControls inputSpecs={inputSpecs} />
            <Button type="submit" fullWidth variant="contained">
              {submitButtonLabel}
            </Button>
          </Stack>
          {children}
        </Card>
      </Stack>
    </Stack>
  );
}
