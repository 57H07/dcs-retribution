// What the engine has to tell the player about the campaign as a whole: its end,
// and problems found when it was loaded (the state itself is in the top bar).
import { useGetTopBarQuery } from "../api/liberationApi";
import { Button, Modal, ModalClose } from "../ui";
import { PATHS } from "./paths";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

export function CampaignNotices() {
  const { data: bar } = useGetTopBarQuery();
  const navigate = useNavigate();
  const state = bar?.campaign_state ?? "continue";
  const warnings = (bar?.warnings ?? []).join("\n");
  const [endClosed, setEndClosed] = useState(false);
  const [readWarnings, setReadWarnings] = useState("");

  // Another campaign can end, or have other warnings.
  useEffect(() => {
    if (state === "continue") {
      setEndClosed(false);
    }
  }, [state]);

  const over = state !== "continue";
  return (
    <>
      <Modal
        title={state === "win" ? "Victory!" : "Defeat!"}
        description={`You have ${state === "win" ? "won" : "lost"} the campaign, do you wish to start a new one?`}
        open={over && !endClosed}
        onOpenChange={(open) => setEndClosed(!open)}
        footer={
          <>
            <ModalClose asChild>
              <Button variant="ghost">Not now</Button>
            </ModalClose>
            <Button
              variant="primary"
              onClick={() => {
                setEndClosed(true);
                navigate(PATHS.newGame);
              }}
            >
              New campaign
            </Button>
          </>
        }
      />
      <Modal
        title="Campaign problems"
        open={!over && warnings !== "" && warnings !== readWarnings}
        onOpenChange={(open) => {
          if (!open) {
            setReadWarnings(warnings);
          }
        }}
      >
        <p style={{ whiteSpace: "pre-line" }}>{warnings}</p>
      </Modal>
    </>
  );
}
