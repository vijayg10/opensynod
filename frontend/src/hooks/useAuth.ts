import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { apiJson } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import type { AuthResponse } from "@/types/api";

interface LoginCredentials {
  username: string;
  password: string;
}

interface RegisterCredentials {
  username: string;
  email: string;
  password: string;
  display_name?: string;
}

export function useAuth() {
  const { user, isAuthenticated, setAuth, clearAuth } = useAuthStore();
  const navigate = useNavigate();

  const loginMutation = useMutation({
    mutationFn: async (credentials: LoginCredentials) => {
      const response = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: credentials.username,
          password: credentials.password,
        }),
        credentials: "include",
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({
          detail: "Login failed",
        }));
        throw new Error(error.detail ?? "Login failed");
      }

      return response.json() as Promise<AuthResponse>;
    },
    onSuccess: (data) => {
      // We don't have user info from login alone — set a minimal user
      setAuth(
        {
          id: "",
          email: "",
          display_name: "",
        },
        data.access_token
      );
      void navigate({ to: "/" });
    },
  });

  const registerMutation = useMutation({
    mutationFn: async (credentials: RegisterCredentials) => {
      return apiJson<AuthResponse>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify(credentials),
      });
    },
    onSuccess: (data) => {
      setAuth(
        {
          id: "",
          email: "",
          display_name: "",
        },
        data.access_token
      );
      void navigate({ to: "/" });
    },
  });

  const logoutMutation = useMutation({
    mutationFn: async () => {
      await apiJson("/api/v1/auth/logout", { method: "POST" });
    },
    onSettled: () => {
      clearAuth();
      void navigate({ to: "/login" });
    },
  });

  return {
    user,
    isAuthenticated,
    login: loginMutation.mutate,
    loginAsync: loginMutation.mutateAsync,
    loginError: loginMutation.error,
    isLoggingIn: loginMutation.isPending,
    register: registerMutation.mutate,
    registerError: registerMutation.error,
    isRegistering: registerMutation.isPending,
    logout: logoutMutation.mutate,
    isLoggingOut: logoutMutation.isPending,
  };
}
