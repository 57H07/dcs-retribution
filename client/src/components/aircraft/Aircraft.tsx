import { Flight } from "../../api/liberationApi";
import { useSymbolIcon } from "../../maplayers/zoom";
import { Marker } from "react-leaflet";

interface AircraftProps {
  flight: Flight;
}

export default function Aircraft(props: AircraftProps) {
  const icon = useSymbolIcon(props.flight.sidc, "flight");
  if (!props.flight.position) {
    return <></>;
  }

  return <Marker position={props.flight.position} icon={icon} />;
}
