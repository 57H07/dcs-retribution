import { _liberationApi } from "./_liberationApi";

// See https://redux-toolkit.js.org/rtk-query/usage/automated-refetching for an
// explanation of tag behavior.

export enum Tags {
  FLIGHT_PLAN = "FlightPlan",
  TOP_BAR = "TopBar",
  SETTINGS = "Settings",
  INSPECTOR = "Inspector",
  MISSION_RESULT = "MissionResult",
  TIMELINE = "Timeline",
  PREFERENCES = "Preferences",
  REPORTS = "Reports",
  PACKAGES = "Packages",
  TRANSFERS = "Transfers",
  BASE = "Base",
  TGO = "Tgo",
  AIR_WING = "AirWing",
}

const LIST_ID = "LIST";

/** What a change to a package touches: the screens and the aircraft it took. */
const PACKAGE_COMMAND_TAGS = [
  Tags.PACKAGES,
  Tags.TOP_BAR,
  Tags.TIMELINE,
  Tags.BASE,
  Tags.INSPECTOR,
];

/** What repairing, selling or buying at a ground object changes. */
const TGO_CHANGES = [
  Tags.TGO,
  Tags.BASE,
  Tags.INSPECTOR,
  Tags.TOP_BAR,
  Tags.REPORTS,
];

function providesList<R extends { id: string | number }[], T extends string>(
  resultsWithIds: R | undefined,
  tagType: T,
) {
  return resultsWithIds
    ? [
        { type: tagType, id: LIST_ID },
        ...resultsWithIds.map(({ id }) => ({ type: tagType, id })),
      ]
    : [{ type: tagType, id: LIST_ID }];
}

export const liberationApi = _liberationApi.enhanceEndpoints({
  addTagTypes: Object.values(Tags),
  endpoints: {
    // /game/ (WEB-01.1): the top bar refreshes after each turn action.
    getTopBar: { providesTags: [Tags.TOP_BAR] },
    passTurn: {
      invalidatesTags: [
        Tags.TOP_BAR,
        Tags.TIMELINE,
        Tags.INSPECTOR,
        Tags.REPORTS,
      ],
    },
    fixTots: { invalidatesTags: [Tags.TOP_BAR, Tags.TIMELINE] },
    // /game/timeline (WEB-01.4): refetched with the top bar on flight events.
    getTimeline: { providesTags: [Tags.TIMELINE] },
    generateMission: { invalidatesTags: [Tags.TOP_BAR, Tags.MISSION_RESULT] },
    // /game/mission/result (WEB-05.1): the waiting screen. Status changes also
    // arrive as `mission_result_updated` events.
    getMissionResult: { providesTags: [Tags.MISSION_RESULT] },
    // /game/mission/result/report (WEB-05.2): the after-action report.
    getMissionReport: { providesTags: [Tags.MISSION_RESULT] },
    loadMissionResultFile: { invalidatesTags: [Tags.MISSION_RESULT] },
    abortMission: {
      invalidatesTags: [Tags.MISSION_RESULT, Tags.TOP_BAR, Tags.TIMELINE],
    },
    acceptMissionResult: {
      invalidatesTags: [
        Tags.MISSION_RESULT,
        Tags.TOP_BAR,
        Tags.TIMELINE,
        Tags.INSPECTOR,
        Tags.REPORTS,
        Tags.PACKAGES,
      ],
    },
    setSimSpeed: { invalidatesTags: [Tags.TOP_BAR] },
    // Map inspector (WEB-01.3): refetched after game changes (eventstream).
    getControlPointSummary: { providesTags: [Tags.INSPECTOR] },
    getTgoSummary: { providesTags: [Tags.INSPECTOR] },
    // Base screen (WEB-02.1): refetched with the inspector (eventstream).
    getBase: { providesTags: [Tags.BASE] },
    orderRepair: {
      invalidatesTags: [
        Tags.BASE,
        Tags.AIR_WING,
        Tags.INSPECTOR,
        Tags.TOP_BAR,
        Tags.REPORTS,
      ],
    },
    orderAllRepairs: {
      invalidatesTags: [
        Tags.BASE,
        Tags.AIR_WING,
        Tags.INSPECTOR,
        Tags.TOP_BAR,
        Tags.REPORTS,
      ],
    },
    // Aircraft orders and new squadrons (WEB-02.2).
    orderAircraft: {
      invalidatesTags: [
        Tags.BASE,
        Tags.AIR_WING,
        Tags.INSPECTOR,
        Tags.TOP_BAR,
        Tags.REPORTS,
      ],
    },
    cancelAircraftOrder: {
      invalidatesTags: [
        Tags.BASE,
        Tags.AIR_WING,
        Tags.INSPECTOR,
        Tags.TOP_BAR,
        Tags.REPORTS,
      ],
    },
    getSquadronChoices: { providesTags: [Tags.BASE] },
    createSquadron: {
      invalidatesTags: [Tags.BASE, Tags.AIR_WING, Tags.INSPECTOR, Tags.REPORTS],
    },
    // Air wing screen (WEB-03): refetched after game changes (eventstream).
    getAirWing: { providesTags: [Tags.AIR_WING] },
    setSquadronPrimaryTask: { invalidatesTags: [Tags.AIR_WING] },
    setSquadronAutoAssign: { invalidatesTags: [Tags.AIR_WING] },
    getSquadronLiveries: { providesTags: [Tags.AIR_WING] },
    setSquadronLivery: { invalidatesTags: [Tags.AIR_WING] },
    getSquadronDestinations: { providesTags: [Tags.AIR_WING] },
    setSquadronDestination: {
      invalidatesTags: [
        Tags.AIR_WING,
        Tags.BASE,
        Tags.INSPECTOR,
        Tags.PACKAGES,
        Tags.TOP_BAR,
        Tags.TIMELINE,
      ],
    },
    createPlayerPilot: { invalidatesTags: [Tags.AIR_WING, Tags.REPORTS] },
    updatePilot: {
      invalidatesTags: [
        Tags.AIR_WING,
        Tags.PACKAGES,
        Tags.TOP_BAR,
        Tags.REPORTS,
      ],
    },
    // Ground forces, convoys, transfers and base actions (WEB-02.3).
    getGroundForces: { providesTags: [Tags.BASE] },
    getDepartingConvoys: { providesTags: [Tags.BASE] },
    getTransferOptions: { providesTags: [Tags.BASE] },
    getBaseActions: { providesTags: [Tags.BASE] },
    orderGroundUnits: {
      invalidatesTags: [Tags.BASE, Tags.INSPECTOR, Tags.TOP_BAR, Tags.REPORTS],
    },
    setFrontLineStance: { invalidatesTags: [Tags.BASE] },
    setBaseRadios: { invalidatesTags: [Tags.BASE] },
    attackDepartingConvoy: { invalidatesTags: PACKAGE_COMMAND_TAGS },
    createTransfer: {
      invalidatesTags: [
        Tags.TRANSFERS,
        Tags.BASE,
        Tags.PACKAGES,
        Tags.INSPECTOR,
        Tags.REPORTS,
        Tags.TOP_BAR,
        Tags.TIMELINE,
      ],
    },
    // The cheats that replan the turn change everything shown.
    cheatMoveFrontLine: {
      invalidatesTags: [
        Tags.BASE,
        Tags.INSPECTOR,
        Tags.PACKAGES,
        Tags.TOP_BAR,
        Tags.TIMELINE,
        Tags.REPORTS,
      ],
    },
    cheatCaptureBase: {
      invalidatesTags: [
        Tags.BASE,
        Tags.INSPECTOR,
        Tags.PACKAGES,
        Tags.TRANSFERS,
        Tags.TOP_BAR,
        Tags.TIMELINE,
        Tags.REPORTS,
      ],
    },
    cheatRunwayState: {
      invalidatesTags: [Tags.BASE, Tags.INSPECTOR, Tags.REPORTS],
    },
    // Ground object sheet (WEB-08.3): refetched with the inspector (eventstream).
    getTgoSheet: { providesTags: [Tags.TGO] },
    repairTgoUnit: { invalidatesTags: TGO_CHANGES },
    setTgoHeading: { invalidatesTags: [Tags.TGO] },
    setTgoHiddenOnMfd: { invalidatesTags: [Tags.TGO] },
    disbandTgoGroup: { invalidatesTags: TGO_CHANGES },
    buyTgoGroup: { invalidatesTags: TGO_CHANGES },
    // /packages/ (WEB-01.2): also refetched on flight events (eventstream.tsx).
    listPackages: { providesTags: [Tags.PACKAGES] },
    deletePackage: { invalidatesTags: PACKAGE_COMMAND_TAGS },
    // Package editor (WEB-04.1).
    getPackage: { providesTags: [Tags.PACKAGES] },
    createPackage: { invalidatesTags: PACKAGE_COMMAND_TAGS },
    renamePackage: { invalidatesTags: [Tags.PACKAGES, Tags.TIMELINE] },
    setPackageTot: { invalidatesTags: PACKAGE_COMMAND_TAGS },
    setPackageTotEarliest: { invalidatesTags: PACKAGE_COMMAND_TAGS },
    getFlightOptions: { providesTags: [Tags.PACKAGES, Tags.BASE] },
    addPackageFlight: { invalidatesTags: PACKAGE_COMMAND_TAGS },
    removePackageFlight: { invalidatesTags: PACKAGE_COMMAND_TAGS },
    getAutoCreateOptions: { providesTags: [Tags.PACKAGES, Tags.BASE] },
    autoCreatePackage: { invalidatesTags: PACKAGE_COMMAND_TAGS },
    // Payload tab (WEB-04.3): follows the flight's size, pilots and events.
    getFlightPayload: { providesTags: [Tags.PACKAGES] },
    setFlightFuel: { invalidatesTags: [Tags.PACKAGES] },
    setSameLoadout: { invalidatesTags: [Tags.PACKAGES] },
    setSameLivery: { invalidatesTags: [Tags.PACKAGES] },
    setMemberLoadout: { invalidatesTags: [Tags.PACKAGES] },
    setMemberCustomLoadout: { invalidatesTags: [Tags.PACKAGES] },
    setMemberPylon: { invalidatesTags: [Tags.PACKAGES] },
    setMemberWeaponSetting: { invalidatesTags: [Tags.PACKAGES] },
    resetMemberWeaponSettings: { invalidatesTags: [Tags.PACKAGES] },
    setMemberTgpLaserCode: { invalidatesTags: [Tags.PACKAGES] },
    setMemberWeaponLaserCode: { invalidatesTags: [Tags.PACKAGES] },
    setMemberLivery: { invalidatesTags: [Tags.PACKAGES] },
    setMemberProperty: { invalidatesTags: [Tags.PACKAGES] },
    saveMemberPayload: { invalidatesTags: [Tags.PACKAGES] },
    // Radios of a flight (WEB-04.5): the warnings look at every other frequency, those
    // of the bases too.
    getFlightRadios: { providesTags: [Tags.PACKAGES, Tags.BASE] },
    setFlightFrequency: { invalidatesTags: [Tags.PACKAGES, Tags.BASE] },
    setPackageFrequency: { invalidatesTags: [Tags.PACKAGES, Tags.BASE] },
    setFlightTacan: { invalidatesTags: [Tags.PACKAGES, Tags.BASE] },
    setFlightDatalink: { invalidatesTags: [Tags.PACKAGES] },
    // /debug/waypoint-geometries
    getDebugHoldZones: {
      providesTags: (result, error, arg) => [
        { type: Tags.FLIGHT_PLAN, id: arg.flightId },
      ],
    },
    getDebugJoinZones: {
      providesTags: (result, error, arg) => [
        { type: Tags.FLIGHT_PLAN, id: arg.flightId },
      ],
    },
    // /flights/
    getCommitBoundaryForFlight: {
      providesTags: (result, error, arg) => [
        { type: Tags.FLIGHT_PLAN, id: arg.flightId },
      ],
    },
    getFlightById: {
      providesTags: (result, error, arg) => [
        { type: Tags.FLIGHT_PLAN, id: arg.flightId },
      ],
    },
    listFlights: {
      providesTags: (result) => providesList(result, Tags.FLIGHT_PLAN),
    },
    // /reports/ (WEB-08.1): refetched with the top bar (new turn, budget...).
    getIntelReport: { providesTags: [Tags.REPORTS] },
    getStatsReport: { providesTags: [Tags.REPORTS] },
    getFinancesReport: { providesTags: [Tags.REPORTS] },
    // WEB-08.2 screens: refetched on mount and with the reports (new turn...).
    listTransfers: { providesTags: [Tags.TRANSFERS, Tags.REPORTS] },
    cancelTransfer: {
      invalidatesTags: [
        Tags.TRANSFERS,
        Tags.BASE,
        Tags.PACKAGES,
        Tags.INSPECTOR,
        Tags.REPORTS,
      ],
    },
    listInformations: { providesTags: [Tags.REPORTS] },
    listCareers: { providesTags: [Tags.REPORTS] },
    // /settings/ (WEB-07.1): a change reloads the whole schema (values, markers).
    getSettings: { providesTags: [Tags.SETTINGS] },
    // A setting (cheats, fast forward...) may change what the top bar shows.
    setSetting: { invalidatesTags: [Tags.SETTINGS, Tags.TOP_BAR] },
    resetSettingsPage: { invalidatesTags: [Tags.SETTINGS, Tags.TOP_BAR] },
    // /preferences/ (WEB-07.2): saving reloads the state (problems, first start).
    getInstallPreferences: { providesTags: [Tags.PREFERENCES] },
    setInstallPreferences: { invalidatesTags: [Tags.PREFERENCES] },
    // /waypoints/
    listAllWaypointsForFlight: {
      providesTags: (result, error, arg) => [
        { type: Tags.FLIGHT_PLAN, id: arg.flightId },
      ],
    },
    setWaypointPosition: {
      invalidatesTags: (result, error, arg) => [
        { type: Tags.FLIGHT_PLAN, id: arg.flightId },
      ],
    },
  },
});

export * from "./_liberationApi";
