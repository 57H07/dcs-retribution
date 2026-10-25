import { Flight } from "../../api/liberationApi";
import { symbolIcon } from "../../maplayers/symbology";
import { Marker } from "react-leaflet";

function iconForFlight(flight: Flight) {
  return symbolIcon(flight.sidc, "flight");
}

interface AircraftProps {
  flight: Flight;
}

export default function Aircraft(props: AircraftProps) {
  if (!props.flight.position) {
    return <></>;
  }

  return (
    <Marker
      position={props.flight.position}
      icon={iconForFlight(props.flight)}
    />
  );
}
