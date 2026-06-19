import { ThemeProvider as MTThemeProvider } from "@material-tailwind/react";

const customTheme = {
  button: {
    valid: {
      colors: ["dark", "slate", "sky", "yellow", "blue", "green", "red"],
    },
    styles: {
      base: {
        initial: {
          fontWeight: "font-bold",
        },
      },
      variants: {
        filled: {
          dark: {
            background: "bg-dark",
            color: "text-white",
          },
        },
        outlined: {
          dark: {
            color: "text-dark",
            border: "border border-dark",
          },
        },
        text: {
          dark: {
            color: "text-dark",
          },
        },
      },
    },
  },
  iconButton: {
    valid: { colors: ["dark"] },
    styles: {
      variants: {
        filled: {
          dark: { background: "bg-dark", color: "text-white" },
        },
        outlined: {
          dark: { color: "text-dark", border: "border border-dark" },
        },
      },
    },
  },
  navbar: {
    valid: { colors: ["dark"] },
    styles: {
      variants: {
        filled: {
          dark: { background: "bg-dark", color: "text-white" },
        },
      },
    },
  },
  card: {
    valid: { colors: ["dark"] },
    styles: {
      variants: {
        filled: {
          dark: { background: "bg-dark" },
        },
      },
    },
  },
  input: {
    valid: {
      colors: ["dark", "slate", "sky", "yellow", "blue", "green", "red"],
    },
  },
};

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <MTThemeProvider value={customTheme as any}>{children}</MTThemeProvider>
  );
}

export default ThemeProvider;
