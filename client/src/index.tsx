import App from "./App";
import { setupStore } from "./app/store";
import { SocketProvider } from "./components/socketprovider/socketprovider";
import "./index.css";
import * as serviceWorker from "./serviceWorker";
import "./theme/fonts.css";
import "./theme/map.css";
import "./theme/tokens.css";
import { applyTheme, themeFromQuery } from "./theme/theme";
import React from "react";
import ReactDOM from "react-dom/client";
import { Provider } from "react-redux";

applyTheme(themeFromQuery(window.location.search));

const root = ReactDOM.createRoot(
  document.getElementById("root") as HTMLElement
);
root.render(
  <React.StrictMode>
    <Provider store={setupStore()}>
      <SocketProvider>
        <App />
      </SocketProvider>
    </Provider>
  </React.StrictMode>
);

// If you want your app to work offline and load faster, you can change
// unregister() to register() below. Note this comes with some pitfalls.
// Learn more about service workers: https://bit.ly/CRA-PWA
serviceWorker.unregister();
