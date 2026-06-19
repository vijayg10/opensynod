import { create } from "zustand";
import { persist } from "zustand/middleware";
import { setAccessToken, clearAccessToken } from "@/lib/api";

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  isAuthenticated: boolean;

  setAuth: (user: AuthUser, token: string) => void;
  setToken: (token: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,

      setAuth: (user, token) => {
        setAccessToken(token);
        set({ user, accessToken: token, isAuthenticated: true });
      },

      setToken: (token) => {
        setAccessToken(token);
        set({ accessToken: token, isAuthenticated: true });
      },

      clearAuth: () => {
        clearAccessToken();
        set({ user: null, accessToken: null, isAuthenticated: false });
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        // Re-apply token to API client after rehydration
        if (state?.accessToken) {
          setAccessToken(state.accessToken);
        }
      },
    }
  )
);
