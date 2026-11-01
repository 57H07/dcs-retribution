// A target picked on the map (WEB-04.1): plans an empty package against it and opens
// the package editor.
import { commandErrorMessage } from "../api/commands";
import { NewPackage, useCreatePackageMutation } from "../api/liberationApi";
import { PATHS } from "../shell/paths";
import { useToast } from "../ui";
import { useCallback } from "react";
import { useNavigate } from "react-router-dom";

export function usePlanPackage(): (target: NewPackage) => void {
  const toast = useToast();
  const navigate = useNavigate();
  const [createPackage] = useCreatePackageMutation();
  return useCallback(
    async (target: NewPackage) => {
      const result = await createPackage({ newPackageJs: target });
      if ("error" in result) {
        toast({
          title: "Could not plan the package",
          description: commandErrorMessage(result.error),
          tone: "danger",
        });
      } else {
        navigate(PATHS.package(result.data.id));
      }
    },
    [createPackage, navigate, toast],
  );
}
