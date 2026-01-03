import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./index.css";
import App from "./App.tsx";

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      {/* TODO(Plan 05): replace <App /> with <RouterProvider router={router} />
          once auth/notes routes exist. App is a placeholder shell for now. */}
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
