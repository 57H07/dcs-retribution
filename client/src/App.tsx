import LiberationMap from "./components/liberationmap";
import useEventStream from "./hooks/useEventSteam";
import useInitialGameState from "./hooks/useInitialGameState";
import { ROUTES } from "./shell/routes";
import { isWebShell } from "./shell/shellMode";
import { createHashRouter, RouterProvider } from "react-router-dom";

// Created on first use: the bare map embedded in the Qt window needs no router.
let router: ReturnType<typeof createHashRouter> | undefined;

interface AppProps {
  /** Query string of the page; `shell=web` selects the full web shell. */
  search?: string;
}

function App({ search = window.location.search }: AppProps) {
  useInitialGameState();
  useEventStream();

  if (isWebShell(search)) {
    // Hash routing: works from file:// and keeps ?server=&apiKey= intact.
    router ??= createHashRouter(ROUTES);
    return <RouterProvider router={router} />;
  }
  return (
    <div className="App">
      <LiberationMap />
    </div>
  );
}

export default App;
