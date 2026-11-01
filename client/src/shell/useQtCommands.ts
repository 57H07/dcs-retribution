// Opens the Qt windows that the web UI does not have yet, through the /qt/*
// routes (WEB-00.3). The server only queues them on the Qt main thread.
// File actions (new, open, save, save as, quit) and external links go through
// the native bridge instead (WEB-00.7, see useNativeCommands).
import { commandErrorMessage } from "../api/commands";
import {
  ExternalLink,
  NativeFolder,
  useOpenControlPointInfoDialogMutation,
  useOpenEditPackageDialogMutation,
} from "../api/liberationApi";
import { useToast } from "../ui";
import { FileAction, useNativeCommands } from "./useNativeCommands";
import { useCallback, useMemo } from "react";

type Result = { error?: unknown } | { data: unknown };

export interface QtCommands {
  openDialog: (action: FileAction) => void;
  openLink: (link: ExternalLink) => void;
  openFolder: (folder: NativeFolder) => void;
  openBase: (controlPointId: string) => void;
  editPackageOfFlight: (flightId: string) => void;
}

export function useQtCommands(): QtCommands {
  const toast = useToast();
  const native = useNativeCommands();
  const [openControlPointInfo] = useOpenControlPointInfoDialogMutation();
  const [openEditPackage] = useOpenEditPackageDialogMutation();

  const report = useCallback(
    (pending: Promise<Result>) => {
      pending.then((result) => {
        if ("error" in result && result.error !== undefined) {
          toast({
            title: "Could not open the screen",
            description: commandErrorMessage(
              result.error as Parameters<typeof commandErrorMessage>[0],
            ),
            tone: "danger",
          });
        }
      });
    },
    [toast],
  );

  return useMemo(
    () => ({
      openDialog: native.runFileAction,
      openLink: native.openLink,
      openFolder: native.openFolder,
      openBase: (cpId) => report(openControlPointInfo({ cpId })),
      editPackageOfFlight: (flightId) =>
        report(openEditPackage({ flightId })),
    }),
    [report, native, openControlPointInfo, openEditPackage],
  );
}
