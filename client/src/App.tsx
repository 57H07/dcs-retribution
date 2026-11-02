import useEventStream from "./hooks/useEventSteam";
import useInitialGameState from "./hooks/useInitialGameState";
import { ROUTES } from "./shell/routes";
import { createHashRouter, RouterProvider } from "react-router-dom";

// Created on first use, so that tests can import this module without a window.
let router: ReturnType<typeof createHashRouter> | undefined;

function App() {
  useInitialGameState();
  useEventStream();

  // Hash routing: works from file:// and keeps ?server=&apiKey= intact.
  router ??= createHashRouter(ROUTES);
  return <RouterProvider router={router} />;
}

export default App;
