// Opens the Qt screens that the web UI does not have yet, through the /qt/*
// routes (WEB-00.3). The server only queues them on the Qt main thread.
import { commandErrorMessage } from "../api/commands";
import {
  QtDialog,
  QtLink,
  useOpenControlPointInfoDialogMutation,
  useOpenEditPackageDialogMutation,
  useOpenExternalLinkMutation,
  useOpenQtDialogMutation,
} from "../api/liberationApi";
import { useToast } from "../ui";
import { useCallback, useMemo } from "react";

type Result = { error?: unknown } | { data: unknown };

export interface QtCommands {
  openDialog: (dialog: QtDialog) => void;
  openLink: (link: QtLink) => void;
  openBase: (controlPointId: string) => void;
  editPackageOfFlight: (flightId: string) => void;
}

export function useQtCommands(): QtCommands {
  const toast = useToast();
  const [openQtDialog] = useOpenQtDialogMutation();
  const [openExternalLink] = useOpenExternalLinkMutation();
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
      openDialog: (dialog) => report(openQtDialog({ dialog })),
      openLink: (link) => report(openExternalLink({ link })),
      openBase: (cpId) => report(openControlPointInfo({ cpId })),
      editPackageOfFlight: (flightId) =>
        report(openEditPackage({ flightId })),
    }),
    [
      report,
      openQtDialog,
      openExternalLink,
      openControlPointInfo,
      openEditPackage,
    ],
  );
}
