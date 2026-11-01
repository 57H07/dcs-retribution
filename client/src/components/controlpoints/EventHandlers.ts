import { ControlPoint } from "../../api/_liberationApi";
import {
  useInspectControlPoint,
  useNewPackage,
} from "../../maplayers/mapSelection";

/**
 * Click: inspector in the web shell, Qt info dialog otherwise (WEB-01.3).
 * Right-click: new package.
 */
export const useLocationMarkerEventHandlers = (controlPoint: ControlPoint) => {
  const inspect = useInspectControlPoint();
  const newPackage = useNewPackage();
  return {
    click: () => {
      inspect(controlPoint.id);
    },

    contextmenu: () => {
      newPackage("control-point", controlPoint.id);
    },
  };
};
