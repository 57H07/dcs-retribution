// What the shell asks of the desktop: file actions (new, open, save, save as, quit),
// folders and external links, all through the native bridge (WEB-00.7, see
// useNativeCommands). No Qt window is left to open from here.
import { ExternalLink, NativeFolder } from "../api/liberationApi";
import { FileAction, useNativeCommands } from "./useNativeCommands";
import { useMemo } from "react";

export interface QtCommands {
  openDialog: (action: FileAction) => void;
  openLink: (link: ExternalLink) => void;
  openFolder: (folder: NativeFolder) => void;
}

export function useQtCommands(): QtCommands {
  const native = useNativeCommands();

  return useMemo(
    () => ({
      openDialog: native.runFileAction,
      openLink: native.openLink,
      openFolder: native.openFolder,
    }),
    [native],
  );
}
