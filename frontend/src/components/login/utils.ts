import { TextFieldSpec } from "@components/login/types";

export const validateName = (
  name: string,
  // @ts-expect-error we pass this function as a prop, and the prop type definition requires
  // this
  formData?: { [key: string]: TextFieldSpec }, // eslint-disable-line @typescript-eslint/no-unused-vars
): [boolean, string] => {
  if (!name) {
    return [true, "Please enter a valid name!"];
  }
  return [false, ""];
};

export const validateUsername = (
  username: string,
  // @ts-expect-error we pass this function as a prop, and the prop type definition requires
  // this
  formData?: { [key: string]: TextFieldSpec }, // eslint-disable-line @typescript-eslint/no-unused-vars
): [boolean, string] => {
  const usernameIsValid = username && /^[a-z\d_]+$/i.test(username);
  if (!usernameIsValid) {
    return [
      true,
      "Usernames can only contain letter, numbers, and underscores. Please enter a valid username!",
    ];
  } else {
    return [false, ""];
  }
};

export const validatePassword = (
  password: string,
  // @ts-expect-error we pass this function as a prop, and the prop type definition requires
  // this
  formData?: { [key: string]: TextFieldSpec }, // eslint-disable-line @typescript-eslint/no-unused-vars
): [boolean, string] => {
  if (!password || password.length < 6) {
    return [true, "Password must be at least six characters long."];
  } else {
    return [false, ""];
  }
};

export const validateSecondPassword = (
  password2: string,
  formData?: { [key: string]: TextFieldSpec },
): [boolean, string] => {
  // If the first password is invalid, do not show another message for password2.
  // Assume that the original password is valid.
  if (typeof formData === "undefined") {
    return [true, ""];
  }
  const origPasswordSpec = formData.password;
  if (typeof origPasswordSpec.value === "undefined") {
    throw new TypeError("Password is not defined in the form data!");
  }
  const origPassword = origPasswordSpec.value;
  if (password2 != origPassword) {
    return [true, "Passwords do not match! Please try again."];
  } else {
    return [false, ""];
  }
};

export const toProperCase = (text: string) => {
  return text[0].toUpperCase() + text.slice(1);
};
