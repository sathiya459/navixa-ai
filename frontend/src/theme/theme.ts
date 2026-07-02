import { createTheme } from "@mui/material/styles";

export const navixaTheme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#0B3D91",
      light: "#3A61A8",
      dark: "#072a66",
    },
    secondary: {
      main: "#1FA2FF",
    },
    background: {
      default: "#F5F7FA",
      paper: "#FFFFFF",
    },
    divider: "#E3E8EF",
    text: {
      primary: "#1A2332",
      secondary: "#5B6B85",
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: { fontWeight: 700 },
    h5: { fontWeight: 700 },
    h6: { fontWeight: 600 },
    subtitle1: { fontWeight: 600 },
    subtitle2: { fontWeight: 600 },
  },
  shape: {
    borderRadius: 10,
  },
  components: {
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: "#FFFFFF",
          color: "#1A2332",
          boxShadow: "none",
          borderBottom: "1px solid #E3E8EF",
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: "#FFFFFF",
          borderRight: "1px solid #E3E8EF",
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
          fontWeight: 600,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: "0 1px 3px rgba(15, 23, 42, 0.08)",
          border: "1px solid #E3E8EF",
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
        },
        elevation1: {
          boxShadow: "0 1px 3px rgba(15, 23, 42, 0.08)",
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 600,
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderColor: "#E3E8EF",
        },
        head: {
          fontWeight: 700,
          color: "#5B6B85",
          textTransform: "uppercase",
          fontSize: "0.72rem",
          letterSpacing: "0.04em",
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          marginBottom: 2,
          "&.Mui-selected": {
            backgroundColor: "rgba(11, 61, 145, 0.08)",
            color: "#0B3D91",
            "& .MuiListItemIcon-root": {
              color: "#0B3D91",
            },
          },
        },
      },
    },
  },
});
