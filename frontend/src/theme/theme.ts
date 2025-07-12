import { createTheme } from "@mui/material";

export const appBarHeight = "64px";
export const drawerWidth = "240px";
const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#6830a1",
      contrastText: "#ffffff",
    },
    secondary: {
      main: "#000000",
    },
    error: {
      main: "#ef4444", // red-500
    },
    warning: {
      main: "#f97316", // orange-500
    },
    info: {
      main: "#0ea5e9", // sky-500
    },
    success: {
      main: "#10b981", // emerald-500
    },
    background: {
      default: "#f9fafb", // gray-50
      paper: "#ffffff", // white
    },
    text: {
      primary: "#111827", // gray-900
      secondary: "#6b7280", // gray-500
    },
    grey: {
      50: "hsl(220, 35%, 97%)",
      100: "hsl(220, 30%, 94%)",
      200: "hsl(220, 20%, 88%)",
      300: "hsl(220, 20%, 80%)",
      400: "hsl(220, 20%, 65%)",
      500: "hsl(220, 20%, 42%)",
      600: "hsl(220, 20%, 35%)",
      700: "hsl(220, 20%, 25%)",
      800: "hsl(220, 30%, 6%)",
      900: "hsl(220, 35%, 3%)",
    },
  },
  typography: {
    fontFamily: `'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'`,
    fontSize: 16,
    fontWeightRegular: 400,
    fontWeightMedium: 500,
    fontWeightBold: 700,
    h1: { fontSize: "2.25rem", fontWeight: 700 },
    h2: { fontSize: "1.875rem", fontWeight: 700 },
    h3: { fontSize: "1.5rem", fontWeight: 600 },
    h4: { fontSize: "1.25rem", fontWeight: 600 },
    h5: { fontSize: "1.125rem", fontWeight: 500 },
    h6: { fontSize: "1rem", fontWeight: 500 },
    body1: { fontSize: "rem" },
    body2: { fontSize: "0.875rem" },
  },
  shape: {
    borderRadius: 8, // Tailwind's rounded-md
  },
  spacing: 4, // Tailwind's default spacing scale (4px per unit)
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none", // remove all-caps
          borderRadius: "0.5rem", // Tailwind's rounded-md (8px)
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: "0.5rem",
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          height: appBarHeight,
          borderBottom: "1px solid lightgray",
          borderRadius: "0rem",
          backgroundColor: "#ffffff",
          paddingLeft: "2rem",
          paddingRight: "2rem",
        },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          backgroundColor: "#fafafa",
        },
      },
    },
    MuiCheckbox: {
      styleOverrides: {
        root: {
          padding: 0,
        },
      },
    },
  },
});

export default theme;
