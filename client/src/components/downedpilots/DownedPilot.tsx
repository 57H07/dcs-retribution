import {
  DownedPilot as DownedPilotModel,
  useOpenNewDownedPilotPackageDialogMutation,
} from "../../api/liberationApi";
import { Icon, Point } from "leaflet";
import { Marker, Tooltip } from "react-leaflet";
import { downedPilotIconDataUrl } from "../../maplayers/downedPilotIcon";

function iconForDownedPilot(pilot: DownedPilotModel) {
  return new Icon({
    iconUrl: downedPilotIconDataUrl(pilot.blue),
    iconSize: new Point(30, 34),
    iconAnchor: new Point(15, 30),
  });
}

interface DownedPilotProps {
  downedPilot: DownedPilotModel;
}

export default function DownedPilot(props: DownedPilotProps) {
  const [openNewPackageDialog] = useOpenNewDownedPilotPackageDialogMutation();
  const pilot = props.downedPilot;
  const turns = pilot.turns_remaining;
  return (
    <Marker
      position={pilot.position}
      icon={iconForDownedPilot(pilot)}
      // Keep downed pilots above other markers; they are time-critical.
      zIndexOffset={2000}
      eventHandlers={{
        contextmenu: () => {
          openNewPackageDialog({ pilotId: pilot.id });
        },
      }}
    >
      <Tooltip>
        <b>{`Downed pilot: ${pilot.name}`}</b>
        <br />
        {`${pilot.squadron} (${pilot.aircraft})`}
        <br />
        {turns === 1
          ? "Last turn to rescue!"
          : `${turns} turns remaining to rescue`}
        <br />
        <i>Right click to plan a CSAR mission</i>
      </Tooltip>
    </Marker>
  );
}
