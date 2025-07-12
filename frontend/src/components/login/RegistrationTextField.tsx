import FormLabel from "@mui/material/FormLabel";
import FormControl from "@mui/material/FormControl";
import TextField from "@mui/material/TextField";

// Components
export default function RegistrationTextField({
  title,
  error,
  errorMessage,
  id,
  type,
  name,
  placeholder,
}: {
  title: string;
  error: boolean;
  errorMessage: string;
  id: string;
  type: string;
  name: string;
  placeholder: string;
}) {
  return (
    <FormControl>
      <FormLabel sx={{ textAlign: "left" }} htmlFor={id}>
        {title}
      </FormLabel>
      <TextField
        error={error}
        helperText={errorMessage}
        id={id}
        type={type}
        name={name}
        placeholder={placeholder}
        autoFocus
        required
        variant="outlined"
        color={error ? "error" : "primary"}
      />
    </FormControl>
  );
}
