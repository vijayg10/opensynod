import {
  createRouter,
  createRootRoute,
  createRoute,
  RouterProvider,
  Outlet,
} from "@tanstack/react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ThemeProvider } from "@/components/ThemeProvider";
import { AuthGuard } from "@/components/AuthGuard";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import SignupPage from "@/pages/SignupPage";
import TopicSetupPage from "@/pages/TopicSetupPage";
import PanelSelectionPage from "@/pages/PanelSelectionPage";
import DiscussionRulesPage from "@/pages/DiscussionRulesPage";
import SessionPage from "@/pages/SessionPage";
import VotingPage from "@/pages/VotingPage";
import OutcomePage from "@/pages/OutcomePage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 2,
    },
  },
});

function RootLayout() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <Outlet />
      </QueryClientProvider>
    </ThemeProvider>
  );
}

const rootRoute = createRootRoute({ component: RootLayout });

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: () => (
    <AuthGuard>
      <DashboardPage />
    </AuthGuard>
  ),
});

const signupRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/signup",
  component: SignupPage,
});

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  component: LoginPage,
});


const topicSetupRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/sessions/new/topic",
  component: () => (
    <AuthGuard>
      <TopicSetupPage />
    </AuthGuard>
  ),
});

const panelSelectionRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/sessions/new/panel",
  component: () => (
    <AuthGuard>
      <PanelSelectionPage />
    </AuthGuard>
  ),
});

const discussionRulesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/sessions/new/rules",
  component: () => (
    <AuthGuard>
      <DiscussionRulesPage />
    </AuthGuard>
  ),
});

const sessionRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/sessions/$sessionId",
  component: () => (
    <AuthGuard>
      <SessionPage />
    </AuthGuard>
  ),
});

const votingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/sessions/$sessionId/vote",
  component: () => (
    <AuthGuard>
      <VotingPage />
    </AuthGuard>
  ),
});

const outcomeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/sessions/$sessionId/outcome",
  component: () => (
    <AuthGuard>
      <OutcomePage />
    </AuthGuard>
  ),
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  signupRoute,
  loginRoute,
  topicSetupRoute,
  panelSelectionRoute,
  discussionRulesRoute,
  sessionRoute,
  votingRoute,
  outcomeRoute,
]);

const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

export default function App() {
  return <RouterProvider router={router} />;
}
