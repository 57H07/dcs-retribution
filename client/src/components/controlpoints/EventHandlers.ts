import { ControlPoint } from "../../api/_liberationApi";
import backend from "../../api/backend";
import { useInspectControlPoint } from "../../maplayers/mapSelection";

function openNewPackageDialog(controlPoint: ControlPoint) {
  backend.post(`/qt/create-package/control-point/${controlPoint.id}`);
}

/**
 * Click: inspector in the web shell, Qt info dialog otherwise (WEB-01.3).
 * Right-click: new package.
 */
export const useLocationMarkerEventHandlers = (controlPoint: ControlPoint) => {
  const inspect = useInspectControlPoint();
  return {
    click: () => {
      inspect(controlPoint.id);
    },

    contextmenu: () => {
      openNewPackageDialog(controlPoint);
    },
  };
};
