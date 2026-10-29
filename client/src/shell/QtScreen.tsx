import { useQtCommands, QtCommands } from "./useQtCommands";
import { useEffect, useRef } from "react";
import { Navigate, Params, useParams } from "react-router-dom";

export interface QtScreenProps {
  /** Opens the Qt screen standing for this route, from the route params. */
  open: (qt: QtCommands, params: Readonly<Params<string>>) => void;
}

/**
 * Route of a screen not migrated yet: opens its Qt dialog once, then returns
 * to the command view. The map stays mounted underneath, so nothing reloads.
 */
export function QtScreen({ open }: QtScreenProps) {
  const qt = useQtCommands();
  const params = useParams();
  // StrictMode runs effects twice in development: open the dialog only once.
  const opened = useRef(false);
  useEffect(() => {
    if (!opened.current) {
      opened.current = true;
      open(qt, params);
    }
  }, [open, qt, params]);
  return <Navigate to="/" replace />;
}
