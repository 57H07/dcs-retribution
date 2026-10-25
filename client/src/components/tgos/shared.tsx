import { Tgo as TgoModel } from "../../api/liberationApi";
import { symbolIcon } from "../../maplayers/symbology";
import SplitLines from "../splitlines/SplitLines";
import { Tooltip } from "react-leaflet";

export function iconForTgo(tgo: TgoModel) {
  return symbolIcon(tgo.sidc, "tgo");
}

export function TgoTooltip(props: { tgo: TgoModel }) {
  return (
    <Tooltip>
      {`${props.tgo.name} (${props.tgo.control_point_name})`}
      <br />
      <SplitLines items={props.tgo.units} />
    </Tooltip>
  );
}
