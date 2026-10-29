import "../base.css";
import "../fonts";
import { installTokens } from "../tokens";
import { Catalog } from "./Catalog";
import React from "react";
import ReactDOM from "react-dom/client";

installTokens();
document.body.classList.add("ui-root");
document.body.style.margin = "0";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <Catalog />
  </React.StrictMode>,
);
