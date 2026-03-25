import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "./contexts/theme";
import { SettingsProvider } from "./contexts/settings";
import { AppLayout } from "./components/layout/app-layout";
import { MeetingPage } from "./pages/meeting-page";
import { SettingsPage } from "./pages/settings-page";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5000, retry: 1 } },
});

export function App() {
  return (
    <ThemeProvider>
      <SettingsProvider>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <Routes>
              <Route element={<AppLayout />}>
                <Route index element={<MeetingPage />} />
                <Route path="meetings/:id" element={<MeetingPage />} />
                <Route path="settings" element={<SettingsPage />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </QueryClientProvider>
      </SettingsProvider>
    </ThemeProvider>
  );
}
