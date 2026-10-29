// Opens the Qt screens that the web UI does not have yet, through the /qt/*
// routes (WEB-00.3). The server only queues them on the Qt main thread.
// File actions (new, open, save, save as, quit) and external links go through
// the native bridge instead (WEB-00.7, see useNativeCommands).
import { commandErrorMessage } from "../api/commands";
import {
  ExternalLink,
  NativeFolder,
  QtDialog,
  useOpenControlPointInfoDialogMutation,
  useOpenEditPackageDialogMutation,
  useOpenQtDialogMutation,
} from "../api/liberationApi";
import { useToast } from "../ui";
import { FileAction, isFileAction, useNativeCommands } from "./useNativeCommands";
import { useCallback, useMemo } from "react";

type Result = { error?: unknown } | { data: unknown };

/** A menu entry of the shell: a Qt screen or a native file action. */
export type ShellDialog = QtDialog | FileAction;

export interface QtCommands {
  openDialog: (dialog: ShellDialog) => void;
  openLink: (link: ExternalLink) => void;
  openFolder: (folder: NativeFolder) => void;
  openBase: (controlPointId: string) => void;
  editPackageOfFlight: (flightId: string) => void;
}

export function useQtCommands(): QtCommands {
  const toast = useToast();
  const native = useNativeCommands();
  const [openQtDialog] = useOpenQtDialogMutation();
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
      openDialog: (dialog) =>
        isFileAction(dialog)
          ? native.runFileAction(dialog)
          : report(openQtDialog({ dialog })),
      openLink: native.openLink,
      openFolder: native.openFolder,
      openBase: (cpId) => report(openControlPointInfo({ cpId })),
      editPackageOfFlight: (flightId) =>
        report(openEditPackage({ flightId })),
    }),
    [report, native, openQtDialog, openControlPointInfo, openEditPackage],
  );
}
