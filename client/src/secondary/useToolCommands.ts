// Tools menu (WEB-08.2): plain API commands, no Qt dialog. Neither needs a file
// dialog: layouts come from the install folders, the Pretense mission goes to
// the missions folder. The server answers once the work is done.
import { commandErrorMessage } from "../api/commands";
import {
  useGeneratePretenseCampaignMutation,
  useImportLayoutsMutation,
} from "../api/liberationApi";
import { useToast } from "../ui";
import { useMemo } from "react";

export interface ToolCommands {
  importLayouts: () => void;
  generatePretenseCampaign: () => void;
}

export function useToolCommands(): ToolCommands {
  const toast = useToast();
  const [importLayouts] = useImportLayoutsMutation();
  const [generatePretense] = useGeneratePretenseCampaignMutation();

  return useMemo(
    () => ({
      importLayouts: () => {
        toast({ title: "Importing layouts…", tone: "info" });
        importLayouts().then((result) => {
          if ("error" in result && result.error !== undefined) {
            toast({
              title: "Could not import the layouts",
              description: commandErrorMessage(result.error),
              tone: "danger",
            });
          } else if ("data" in result) {
            toast({
              title: "Layouts imported",
              description: `${result.data.count} layouts available.`,
              tone: "success",
            });
          }
        });
      },
      generatePretenseCampaign: () => {
        toast({ title: "Generating the Pretense campaign…", tone: "info" });
        generatePretense().then((result) => {
          if ("error" in result && result.error !== undefined) {
            toast({
              title: "Could not generate the Pretense campaign",
              description: commandErrorMessage(result.error),
              tone: "danger",
            });
          } else if ("data" in result) {
            toast({
              title: "Pretense campaign generated",
              description: result.data.path,
              tone: "success",
            });
          }
        });
      },
    }),
    [toast, importLayouts, generatePretense],
  );
}
