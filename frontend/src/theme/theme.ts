import { createTheme } from "@mui/material/styles";

export const navixaTheme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#0B3D91",
    },
    secondary: {
      main: "#1FA2FF",
    },
    background: {
      default: "#F5F7FA",
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  },
  shape: {
    borderRadius: 8,
  },
});
