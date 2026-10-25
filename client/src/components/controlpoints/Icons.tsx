import { ControlPoint } from "../../api/_liberationApi";
import { symbolIcon } from "../../maplayers/symbology";

export const iconForControlPoint = (cp: ControlPoint) =>
  symbolIcon(cp.sidc, "controlPoint");
