// In-campaign air wing configuration (WEB-06): the Faction and Cheats tabs of the Qt
// air wing dialog, open when the "Enable Air Wing adjustments" cheat is on. The
// server refuses it otherwise, and the panel shows why.
import { ScreenFrame } from "../secondary/ScreenFrame";
import { AirWingConfigPanel } from "./AirWingConfigPanel";

export function AirWingConfigScreen() {
  return (
    <ScreenFrame title="Air wing adjustments">
      <AirWingConfigPanel target="campaign" />
    </ScreenFrame>
  );
}
