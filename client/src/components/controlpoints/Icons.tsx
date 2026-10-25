import { ControlPoint } from "../../api/_liberationApi";
import { useSymbolIcon } from "../../maplayers/zoom";

// Symbol of a control point, sized for the current map zoom.
export const useControlPointIcon = (cp: ControlPoint) =>
  useSymbolIcon(cp.sidc, "controlPoint");
