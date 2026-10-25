import { LatLng } from "../../api/liberationApi";
import { LAYER_COLORS } from "../../maplayers/colors";
import { Polygon } from "react-leaflet";

interface ThreatZoneProps {
  poly: LatLng[][];
  blue: boolean;
}

export default function ThreatZone(props: ThreatZoneProps) {
  const color = props.blue
    ? LAYER_COLORS.threatBlue
    : LAYER_COLORS.threatRed;
  return (
    <Polygon
      positions={props.poly}
      color={color}
      weight={1}
      fill
      fillOpacity={0.4}
      noClip
      interactive={false}
    />
  );
}
