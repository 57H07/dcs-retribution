// "Take off" (WEB-01.1): the confirmations of QTopPanel.launch_mission, in the
// same order, then the generate-mission command. The server decides what needs
// confirming (GET /game/mission/checks) and refuses missing pilots itself. Once
// the mission is written, the waiting screen takes over (WEB-05.1).
import { commandErrorMessage } from "../api/commands";
import {
  MissionChecks,
  liberationApi,
  useFixTotsMutation,
  useGenerateMissionMutation,
} from "../api/liberationApi";
import { useAppDispatch } from "../app/hooks";
import { PATHS } from "../shell/paths";
import { useToast } from "../ui";
import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";

export type TakeOffStep =
  | { kind: "idle" }
  | { kind: "checking" }
  | { kind: "noPlayer"; checks: MissionChecks }
  | { kind: "missingPilots"; flights: string[] }
  | { kind: "pastStart"; packages: string[] }
  | { kind: "launching" };

export interface TakeOff {
  step: TakeOffStep;
  start: () => void;
  /** "Continue without player pilots?" answered Yes. */
  continueWithoutPlayers: () => void;
  /** Past start times: fix the TOTs, then take off. */
  fixTotsAndLaunch: () => void;
  /** Past start times: take off as planned. */
  launchAnyway: () => void;
  cancel: () => void;
}

export function useTakeOff(): TakeOff {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const toast = useToast();
  const [fixTots] = useFixTotsMutation();
  const [generateMission] = useGenerateMissionMutation();
  const [step, setStep] = useState<TakeOffStep>({ kind: "idle" });

  const fail = useCallback(
    (title: string, error: unknown) => {
      setStep({ kind: "idle" });
      toast({
        title,
        description: commandErrorMessage(
          error as Parameters<typeof commandErrorMessage>[0],
        ),
        tone: "danger",
      });
    },
    [toast],
  );

  const launch = useCallback(async () => {
    setStep({ kind: "launching" });
    const result = await generateMission();
    if ("error" in result) {
      fail("Could not take off", result.error);
      return;
    }
    setStep({ kind: "idle" });
    toast({
      title: "Mission generated",
      description: `Start ${result.data.path} in DCS, then wait for the result.`,
      tone: "success",
    });
    navigate(PATHS.waiting);
  }, [generateMission, fail, toast, navigate]);

  // After the player-pilot question: missing pilots block, past starts ask.
  const afterPlayers = useCallback(
    (checks: MissionChecks) => {
      if (checks.flights_missing_pilots.length > 0) {
        setStep({
          kind: "missingPilots",
          flights: checks.flights_missing_pilots,
        });
      } else if (checks.packages_starting_in_the_past.length > 0) {
        setStep({
          kind: "pastStart",
          packages: checks.packages_starting_in_the_past,
        });
      } else {
        launch();
      }
    },
    [launch],
  );

  const start = useCallback(async () => {
    setStep({ kind: "checking" });
    const query = dispatch(
      liberationApi.endpoints.getMissionChecks.initiate(undefined, {
        forceRefetch: true,
      }),
    );
    const result = await query;
    query.unsubscribe();
    if (result.error !== undefined || result.data === undefined) {
      fail("Could not check the mission", result.error);
      return;
    }
    if (!result.data.has_player_pilots) {
      setStep({ kind: "noPlayer", checks: result.data });
    } else {
      afterPlayers(result.data);
    }
  }, [dispatch, fail, afterPlayers]);

  const continueWithoutPlayers = useCallback(() => {
    if (step.kind === "noPlayer") {
      afterPlayers(step.checks);
    }
  }, [step, afterPlayers]);

  const fixTotsAndLaunch = useCallback(async () => {
    setStep({ kind: "launching" });
    const result = await fixTots();
    if ("error" in result) {
      fail("Could not fix the TOTs", result.error);
      return;
    }
    launch();
  }, [fixTots, fail, launch]);

  return {
    step,
    start,
    continueWithoutPlayers,
    fixTotsAndLaunch,
    launchAnyway: launch,
    cancel: () => setStep({ kind: "idle" }),
  };
}
