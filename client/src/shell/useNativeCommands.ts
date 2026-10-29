// System actions of the web UI through the native bridge (WEB-00.7, W7): file
// dialogs, folders, external links and quit, served by the /native/* routes.
// A file route answers once the player closed the dialog, with what happened.
import { commandErrorMessage } from "../api/commands";
import {
  ExternalLink,
  FileActionResult,
  NativeFolder,
  useOpenExternalLinkMutation,
  useOpenGameMutation,
  useOpenNativeFolderMutation,
  useOpenNewGameWizardMutation,
  useQuitApplicationMutation,
  useSaveGameAsMutation,
  useSaveGameMutation,
} from "../api/liberationApi";
import { ToastOptions, useToast } from "../ui";
import { useCallback, useMemo } from "react";

/** File menu entries served by the native bridge instead of a Qt dialog. */
export const FILE_ACTIONS = [
  "new-game",
  "open-game",
  "save-game",
  "save-game-as",
  "quit",
] as const;

export type FileAction = (typeof FILE_ACTIONS)[number];

export function isFileAction(value: string): value is FileAction {
  return (FILE_ACTIONS as readonly string[]).includes(value);
}

export interface NativeCommands {
  runFileAction: (action: FileAction) => void;
  openLink: (link: ExternalLink) => void;
  openFolder: (folder: NativeFolder) => void;
}

type Result = { error?: unknown; data?: unknown };
type CommandError = Parameters<typeof commandErrorMessage>[0];

/** Toast telling how a save or open ended. */
export function fileResultToast(
  action: "save" | "open",
  result: FileActionResult,
): ToastOptions {
  if (result.outcome === "cancelled") {
    return {
      title: action === "save" ? "Save cancelled" : "Open cancelled",
      tone: "info",
    };
  }
  return {
    title: result.outcome === "saved" ? "Campaign saved" : "Campaign opened",
    description: result.path ?? undefined,
    tone: "success",
  };
}

export function useNativeCommands(): NativeCommands {
  const toast = useToast();
  const [saveGame] = useSaveGameMutation();
  const [saveGameAs] = useSaveGameAsMutation();
  const [openGame] = useOpenGameMutation();
  const [openNewGameWizard] = useOpenNewGameWizardMutation();
  const [quitApplication] = useQuitApplicationMutation();
  const [openExternalLink] = useOpenExternalLinkMutation();
  const [openNativeFolder] = useOpenNativeFolderMutation();

  const report = useCallback(
    (
      pending: Promise<Result>,
      failure: string,
      success?: (data: unknown) => ToastOptions,
    ) => {
      pending.then((result) => {
        if (result.error !== undefined) {
          toast({
            title: failure,
            description: commandErrorMessage(result.error as CommandError),
            tone: "danger",
          });
        } else if (success) {
          toast(success(result.data));
        }
      });
    },
    [toast],
  );

  return useMemo(() => {
    const fileResult = (action: "save" | "open") => (data: unknown) =>
      fileResultToast(action, data as FileActionResult);
    const runFileAction = (action: FileAction) => {
      switch (action) {
        case "save-game":
          report(saveGame(), "Could not save the campaign", fileResult("save"));
          break;
        case "save-game-as":
          report(
            saveGameAs(),
            "Could not save the campaign",
            fileResult("save"),
          );
          break;
        case "open-game":
          report(openGame(), "Could not open the campaign", fileResult("open"));
          break;
        case "new-game":
          report(openNewGameWizard(), "Could not start a new campaign");
          break;
        case "quit":
          report(quitApplication(), "Could not quit");
          break;
      }
    };
    return {
      runFileAction,
      openLink: (link) =>
        report(openExternalLink({ link }), "Could not open the link"),
      openFolder: (folder) =>
        report(openNativeFolder({ folder }), "Could not open the folder"),
    };
  }, [
    report,
    saveGame,
    saveGameAs,
    openGame,
    openNewGameWizard,
    quitApplication,
    openExternalLink,
    openNativeFolder,
  ]);
}
