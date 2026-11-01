import { FrontLine as FrontLineModel } from "../../api/liberationApi";
import { useNewPackage } from "../../maplayers/mapSelection";
import { FRONT_LINE_WEIGHT, LAYER_COLORS } from "../../maplayers/colors";
import { Polyline } from "react-leaflet";

interface FrontLineProps {
  front: FrontLineModel;
}

function FrontLine(props: FrontLineProps) {
  const newPackage = useNewPackage();
  return (
    <Polyline
      positions={props.front.extents}
      weight={FRONT_LINE_WEIGHT}
      color={LAYER_COLORS.frontLine}
      eventHandlers={{
        contextmenu: () => {
          newPackage("front-line", props.front.id);
        },
      }}
    />
  );
}

export default FrontLine;
