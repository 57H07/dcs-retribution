import { baseApi as api } from "./baseApi";
const injectedRtkApi = api.injectEndpoints({
  endpoints: (build) => ({
    listControlPoints: build.query<
      ListControlPointsApiResponse,
      ListControlPointsApiArg
    >({
      query: () => ({ url: `/control-points/` }),
    }),
    getControlPointById: build.query<
      GetControlPointByIdApiResponse,
      GetControlPointByIdApiArg
    >({
      query: (queryArg) => ({ url: `/control-points/${queryArg.cpId}` }),
    }),
    getControlPointSummary: build.query<
      GetControlPointSummaryApiResponse,
      GetControlPointSummaryApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/summary`,
      }),
    }),
    getBase: build.query<GetBaseApiResponse, GetBaseApiArg>({
      query: (queryArg) => ({ url: `/control-points/${queryArg.cpId}/base` }),
    }),
    orderRepair: build.mutation<OrderRepairApiResponse, OrderRepairApiArg>({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/repairs/${queryArg.repairId}`,
        method: "POST",
      }),
    }),
    orderAllRepairs: build.mutation<
      OrderAllRepairsApiResponse,
      OrderAllRepairsApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/repair-all`,
        method: "POST",
      }),
    }),
    orderAircraft: build.mutation<
      OrderAircraftApiResponse,
      OrderAircraftApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/purchases/aircraft`,
        method: "POST",
        body: queryArg.aircraftOrdersJs,
      }),
    }),
    cancelAircraftOrder: build.mutation<
      CancelAircraftOrderApiResponse,
      CancelAircraftOrderApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/purchases/aircraft/${queryArg.squadronId}`,
        method: "DELETE",
      }),
    }),
    getSquadronChoices: build.query<
      GetSquadronChoicesApiResponse,
      GetSquadronChoicesApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/squadron-choices`,
      }),
    }),
    createSquadron: build.mutation<
      CreateSquadronApiResponse,
      CreateSquadronApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/squadrons`,
        method: "POST",
        body: queryArg.newSquadronJs,
      }),
    }),
    controlPointDestinationInRange: build.query<
      ControlPointDestinationInRangeApiResponse,
      ControlPointDestinationInRangeApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/destination-in-range`,
        params: { lat: queryArg.lat, lng: queryArg.lng },
      }),
    }),
    setControlPointDestination: build.mutation<
      SetControlPointDestinationApiResponse,
      SetControlPointDestinationApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/destination`,
        method: "PUT",
        body: queryArg.leafletPoint,
      }),
    }),
    clearControlPointDestination: build.mutation<
      ClearControlPointDestinationApiResponse,
      ClearControlPointDestinationApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/cancel-travel`,
        method: "PUT",
      }),
    }),
    getDebugHoldZones: build.query<
      GetDebugHoldZonesApiResponse,
      GetDebugHoldZonesApiArg
    >({
      query: (queryArg) => ({
        url: `/debug/waypoint-geometries/hold/${queryArg.flightId}`,
      }),
    }),
    getDebugJoinZones: build.query<
      GetDebugJoinZonesApiResponse,
      GetDebugJoinZonesApiArg
    >({
      query: (queryArg) => ({
        url: `/debug/waypoint-geometries/join/${queryArg.flightId}`,
      }),
    }),
    listDownedPilots: build.query<
      ListDownedPilotsApiResponse,
      ListDownedPilotsApiArg
    >({
      query: () => ({ url: `/downed-pilots/` }),
    }),
    getDownedPilotById: build.query<
      GetDownedPilotByIdApiResponse,
      GetDownedPilotByIdApiArg
    >({
      query: (queryArg) => ({ url: `/downed-pilots/${queryArg.pilotId}` }),
    }),
    listFlights: build.query<ListFlightsApiResponse, ListFlightsApiArg>({
      query: (queryArg) => ({
        url: `/flights/`,
        params: { with_waypoints: queryArg.withWaypoints },
      }),
    }),
    getFlightById: build.query<GetFlightByIdApiResponse, GetFlightByIdApiArg>({
      query: (queryArg) => ({
        url: `/flights/${queryArg.flightId}`,
        params: { with_waypoints: queryArg.withWaypoints },
      }),
    }),
    getCommitBoundaryForFlight: build.query<
      GetCommitBoundaryForFlightApiResponse,
      GetCommitBoundaryForFlightApiArg
    >({
      query: (queryArg) => ({
        url: `/flights/${queryArg.flightId}/commit-boundary`,
      }),
    }),
    listFrontLines: build.query<
      ListFrontLinesApiResponse,
      ListFrontLinesApiArg
    >({
      query: () => ({ url: `/front-lines/` }),
    }),
    getFrontLineById: build.query<
      GetFrontLineByIdApiResponse,
      GetFrontLineByIdApiArg
    >({
      query: (queryArg) => ({ url: `/front-lines/${queryArg.frontLineId}` }),
    }),
    getGameState: build.query<GetGameStateApiResponse, GetGameStateApiArg>({
      query: () => ({ url: `/game/` }),
    }),
    getTopBar: build.query<GetTopBarApiResponse, GetTopBarApiArg>({
      query: () => ({ url: `/game/top-bar` }),
    }),
    getTimeline: build.query<GetTimelineApiResponse, GetTimelineApiArg>({
      query: () => ({ url: `/game/timeline` }),
    }),
    passTurn: build.mutation<PassTurnApiResponse, PassTurnApiArg>({
      query: () => ({ url: `/game/turn/pass`, method: "POST" }),
    }),
    getMissionChecks: build.query<
      GetMissionChecksApiResponse,
      GetMissionChecksApiArg
    >({
      query: () => ({ url: `/game/mission/checks` }),
    }),
    fixTots: build.mutation<FixTotsApiResponse, FixTotsApiArg>({
      query: () => ({ url: `/game/mission/fix-tots`, method: "POST" }),
    }),
    generateMission: build.mutation<
      GenerateMissionApiResponse,
      GenerateMissionApiArg
    >({
      query: () => ({ url: `/game/mission`, method: "POST" }),
    }),
    setSimSpeed: build.mutation<SetSimSpeedApiResponse, SetSimSpeedApiArg>({
      query: (queryArg) => ({
        url: `/game/sim/speed`,
        method: "PUT",
        body: queryArg.simSpeedChangeJs,
      }),
    }),
    getSettings: build.query<GetSettingsApiResponse, GetSettingsApiArg>({
      query: () => ({ url: `/settings/` }),
    }),
    setSetting: build.mutation<SetSettingApiResponse, SetSettingApiArg>({
      query: (queryArg) => ({
        url: `/settings/values/${queryArg.key}`,
        method: "PUT",
        body: queryArg.settingValueUpdateJs,
      }),
    }),
    resetSettingsPage: build.mutation<
      ResetSettingsPageApiResponse,
      ResetSettingsPageApiArg
    >({
      query: (queryArg) => ({
        url: `/settings/pages/${queryArg.pageId}/reset`,
        method: "POST",
      }),
    }),
    getTerrainZones: build.query<
      GetTerrainZonesApiResponse,
      GetTerrainZonesApiArg
    >({
      query: () => ({ url: `/map-zones/terrain` }),
    }),
    getOfflineBasemapImage: build.query<
      GetOfflineBasemapImageApiResponse,
      GetOfflineBasemapImageApiArg
    >({
      query: (queryArg) => ({
        url: `/map-zones/offline-basemap`,
        params: {
          sea: queryArg.sea,
          land: queryArg.land,
          land_excluded: queryArg.landExcluded,
          coastline: queryArg.coastline,
        },
      }),
    }),
    listUnculledZones: build.query<
      ListUnculledZonesApiResponse,
      ListUnculledZonesApiArg
    >({
      query: () => ({ url: `/map-zones/unculled` }),
    }),
    getThreatZones: build.query<
      GetThreatZonesApiResponse,
      GetThreatZonesApiArg
    >({
      query: () => ({ url: `/map-zones/threats` }),
    }),
    getMissionResult: build.query<
      GetMissionResultApiResponse,
      GetMissionResultApiArg
    >({
      query: () => ({ url: `/game/mission/result` }),
    }),
    getMissionReport: build.query<
      GetMissionReportApiResponse,
      GetMissionReportApiArg
    >({
      query: () => ({ url: `/game/mission/result/report` }),
    }),
    loadMissionResultFile: build.mutation<
      LoadMissionResultFileApiResponse,
      LoadMissionResultFileApiArg
    >({
      query: () => ({ url: `/game/mission/result/file`, method: "POST" }),
    }),
    abortMission: build.mutation<AbortMissionApiResponse, AbortMissionApiArg>({
      query: () => ({ url: `/game/mission/result/cancel`, method: "POST" }),
    }),
    acceptMissionResult: build.mutation<
      AcceptMissionResultApiResponse,
      AcceptMissionResultApiArg
    >({
      query: () => ({ url: `/game/mission/result/accept`, method: "POST" }),
    }),
    saveGame: build.mutation<SaveGameApiResponse, SaveGameApiArg>({
      query: () => ({ url: `/native/save`, method: "POST" }),
    }),
    saveGameAs: build.mutation<SaveGameAsApiResponse, SaveGameAsApiArg>({
      query: () => ({ url: `/native/save-as`, method: "POST" }),
    }),
    openGame: build.mutation<OpenGameApiResponse, OpenGameApiArg>({
      query: () => ({ url: `/native/open`, method: "POST" }),
    }),
    pickFolder: build.mutation<PickFolderApiResponse, PickFolderApiArg>({
      query: (queryArg) => ({
        url: `/native/pick-folder`,
        method: "POST",
        body: queryArg.folderPickRequestJs,
      }),
    }),
    openNewGameWizard: build.mutation<
      OpenNewGameWizardApiResponse,
      OpenNewGameWizardApiArg
    >({
      query: () => ({ url: `/native/new-game`, method: "POST" }),
    }),
    openNativeFolder: build.mutation<
      OpenNativeFolderApiResponse,
      OpenNativeFolderApiArg
    >({
      query: (queryArg) => ({
        url: `/native/open-folder/${queryArg.folder}`,
        method: "POST",
      }),
    }),
    openExternalLink: build.mutation<
      OpenExternalLinkApiResponse,
      OpenExternalLinkApiArg
    >({
      query: (queryArg) => ({
        url: `/native/open-link/${queryArg.link}`,
        method: "POST",
      }),
    }),
    quitApplication: build.mutation<
      QuitApplicationApiResponse,
      QuitApplicationApiArg
    >({
      query: () => ({ url: `/native/quit`, method: "POST" }),
    }),
    getNavmesh: build.query<GetNavmeshApiResponse, GetNavmeshApiArg>({
      query: (queryArg) => ({
        url: `/navmesh/`,
        params: { for_player: queryArg.forPlayer },
      }),
    }),
    listPackages: build.query<ListPackagesApiResponse, ListPackagesApiArg>({
      query: () => ({ url: `/packages/` }),
    }),
    createPackage: build.mutation<
      CreatePackageApiResponse,
      CreatePackageApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/`,
        method: "POST",
        body: queryArg.newPackageJs,
      }),
    }),
    deletePackage: build.mutation<
      DeletePackageApiResponse,
      DeletePackageApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}`,
        method: "DELETE",
      }),
    }),
    getInstallPreferences: build.query<
      GetInstallPreferencesApiResponse,
      GetInstallPreferencesApiArg
    >({
      query: () => ({ url: `/preferences/` }),
    }),
    setInstallPreferences: build.mutation<
      SetInstallPreferencesApiResponse,
      SetInstallPreferencesApiArg
    >({
      query: (queryArg) => ({
        url: `/preferences/`,
        method: "PUT",
        body: queryArg.installPreferencesUpdateJs,
      }),
    }),
    openNewFrontLinePackageDialog: build.mutation<
      OpenNewFrontLinePackageDialogApiResponse,
      OpenNewFrontLinePackageDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/create-package/front-line/${queryArg.frontLineId}`,
        method: "POST",
      }),
    }),
    openNewTgoPackageDialog: build.mutation<
      OpenNewTgoPackageDialogApiResponse,
      OpenNewTgoPackageDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/create-package/tgo/${queryArg.tgoId}`,
        method: "POST",
      }),
    }),
    openTgoInfoDialog: build.mutation<
      OpenTgoInfoDialogApiResponse,
      OpenTgoInfoDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/info/tgo/${queryArg.tgoId}`,
        method: "POST",
      }),
    }),
    openNewControlPointPackageDialog: build.mutation<
      OpenNewControlPointPackageDialogApiResponse,
      OpenNewControlPointPackageDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/create-package/control-point/${queryArg.cpId}`,
        method: "POST",
      }),
    }),
    openNewDownedPilotPackageDialog: build.mutation<
      OpenNewDownedPilotPackageDialogApiResponse,
      OpenNewDownedPilotPackageDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/create-package/downed-pilot/${queryArg.pilotId}`,
        method: "POST",
      }),
    }),
    selectFlight: build.mutation<SelectFlightApiResponse, SelectFlightApiArg>({
      query: (queryArg) => ({
        url: `/qt/select-flight/${queryArg.flightId}`,
        method: "POST",
      }),
    }),
    openControlPointInfoDialog: build.mutation<
      OpenControlPointInfoDialogApiResponse,
      OpenControlPointInfoDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/info/control-point/${queryArg.cpId}`,
        method: "POST",
      }),
    }),
    openQtDialog: build.mutation<OpenQtDialogApiResponse, OpenQtDialogApiArg>({
      query: (queryArg) => ({
        url: `/qt/dialogs/${queryArg.dialog}`,
        method: "POST",
      }),
    }),
    openEditPackageDialog: build.mutation<
      OpenEditPackageDialogApiResponse,
      OpenEditPackageDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/edit-package/flight/${queryArg.flightId}`,
        method: "POST",
      }),
    }),
    getIntelReport: build.query<
      GetIntelReportApiResponse,
      GetIntelReportApiArg
    >({
      query: () => ({ url: `/reports/intel` }),
    }),
    getStatsReport: build.query<
      GetStatsReportApiResponse,
      GetStatsReportApiArg
    >({
      query: () => ({ url: `/reports/stats` }),
    }),
    getFinancesReport: build.query<
      GetFinancesReportApiResponse,
      GetFinancesReportApiArg
    >({
      query: () => ({ url: `/reports/finances` }),
    }),
    listSupplyRoutes: build.query<
      ListSupplyRoutesApiResponse,
      ListSupplyRoutesApiArg
    >({
      query: () => ({ url: `/supply-routes/` }),
    }),
    listTgos: build.query<ListTgosApiResponse, ListTgosApiArg>({
      query: () => ({ url: `/tgos/` }),
    }),
    getTgoById: build.query<GetTgoByIdApiResponse, GetTgoByIdApiArg>({
      query: (queryArg) => ({ url: `/tgos/${queryArg.tgoId}` }),
    }),
    getTgoSummary: build.query<GetTgoSummaryApiResponse, GetTgoSummaryApiArg>({
      query: (queryArg) => ({ url: `/tgos/${queryArg.tgoId}/summary` }),
    }),
    tgoDestinationInRange: build.query<
      TgoDestinationInRangeApiResponse,
      TgoDestinationInRangeApiArg
    >({
      query: (queryArg) => ({
        url: `/tgos/${queryArg.tgoId}/destination-in-range`,
        params: { lat: queryArg.lat, lng: queryArg.lng },
      }),
    }),
    setTgoDestination: build.mutation<
      SetTgoDestinationApiResponse,
      SetTgoDestinationApiArg
    >({
      query: (queryArg) => ({
        url: `/tgos/${queryArg.tgoId}/destination`,
        method: "PUT",
        body: queryArg.leafletPoint,
      }),
    }),
    clearTgoDestination: build.mutation<
      ClearTgoDestinationApiResponse,
      ClearTgoDestinationApiArg
    >({
      query: (queryArg) => ({
        url: `/tgos/${queryArg.tgoId}/cancel-travel`,
        method: "PUT",
      }),
    }),
    listAllWaypointsForFlight: build.query<
      ListAllWaypointsForFlightApiResponse,
      ListAllWaypointsForFlightApiArg
    >({
      query: (queryArg) => ({ url: `/waypoints/${queryArg.flightId}` }),
    }),
    setWaypointPosition: build.mutation<
      SetWaypointPositionApiResponse,
      SetWaypointPositionApiArg
    >({
      query: (queryArg) => ({
        url: `/waypoints/${queryArg.flightId}/${queryArg.waypointIdx}/position`,
        method: "POST",
        body: queryArg.leafletPoint,
      }),
    }),
    getIadsNetwork: build.query<
      GetIadsNetworkApiResponse,
      GetIadsNetworkApiArg
    >({
      query: () => ({ url: `/iads-network/` }),
    }),
    getIadsConnectionsForTgo: build.query<
      GetIadsConnectionsForTgoApiResponse,
      GetIadsConnectionsForTgoApiArg
    >({
      query: (queryArg) => ({ url: `/iads-network/for-tgo/${queryArg.tgoId}` }),
    }),
    getLogs: build.query<GetLogsApiResponse, GetLogsApiArg>({
      query: (queryArg) => ({
        url: `/logs`,
        params: { lines: queryArg.lines },
      }),
    }),
    getAbout: build.query<GetAboutApiResponse, GetAboutApiArg>({
      query: () => ({ url: `/about` }),
    }),
    listCareers: build.query<ListCareersApiResponse, ListCareersApiArg>({
      query: () => ({ url: `/careers/` }),
    }),
    getNotes: build.query<GetNotesApiResponse, GetNotesApiArg>({
      query: () => ({ url: `/notes` }),
    }),
    setNotes: build.mutation<SetNotesApiResponse, SetNotesApiArg>({
      query: (queryArg) => ({
        url: `/notes`,
        method: "PUT",
        body: queryArg.notesJs,
      }),
    }),
    listInformations: build.query<
      ListInformationsApiResponse,
      ListInformationsApiArg
    >({
      query: () => ({ url: `/informations` }),
    }),
    importLayouts: build.mutation<
      ImportLayoutsApiResponse,
      ImportLayoutsApiArg
    >({
      query: () => ({ url: `/tools/import-layouts`, method: "POST" }),
    }),
    generatePretenseCampaign: build.mutation<
      GeneratePretenseCampaignApiResponse,
      GeneratePretenseCampaignApiArg
    >({
      query: () => ({ url: `/tools/pretense-campaign`, method: "POST" }),
    }),
    listTransfers: build.query<ListTransfersApiResponse, ListTransfersApiArg>({
      query: () => ({ url: `/transfers/` }),
    }),
    cancelTransfer: build.mutation<
      CancelTransferApiResponse,
      CancelTransferApiArg
    >({
      query: (queryArg) => ({
        url: `/transfers/${queryArg.transferId}`,
        method: "DELETE",
      }),
    }),
  }),
  overrideExisting: false,
});
export { injectedRtkApi as _liberationApi };
export type ListControlPointsApiResponse =
  /** status 200 Successful Response */ ControlPoint[];
export type ListControlPointsApiArg = void;
export type GetControlPointByIdApiResponse =
  /** status 200 Successful Response */ ControlPoint;
export type GetControlPointByIdApiArg = {
  cpId: string;
};
export type GetControlPointSummaryApiResponse =
  /** status 200 Successful Response */ ControlPointSummary;
export type GetControlPointSummaryApiArg = {
  cpId: string;
};
export type GetBaseApiResponse = /** status 200 Successful Response */ Base;
export type GetBaseApiArg = {
  cpId: string;
};
export type OrderRepairApiResponse = /** status 200 Successful Response */ Base;
export type OrderRepairApiArg = {
  cpId: string;
  repairId: string;
};
export type OrderAllRepairsApiResponse =
  /** status 200 Successful Response */ Base;
export type OrderAllRepairsApiArg = {
  cpId: string;
};
export type OrderAircraftApiResponse =
  /** status 200 Successful Response */ Base;
export type OrderAircraftApiArg = {
  cpId: string;
  aircraftOrdersJs: AircraftOrders;
};
export type CancelAircraftOrderApiResponse =
  /** status 200 Successful Response */ Base;
export type CancelAircraftOrderApiArg = {
  cpId: string;
  squadronId: string;
};
export type GetSquadronChoicesApiResponse =
  /** status 200 Successful Response */ SquadronChoice[];
export type GetSquadronChoicesApiArg = {
  cpId: string;
};
export type CreateSquadronApiResponse =
  /** status 200 Successful Response */ Base;
export type CreateSquadronApiArg = {
  cpId: string;
  newSquadronJs: NewSquadron;
};
export type ControlPointDestinationInRangeApiResponse =
  /** status 200 Successful Response */ boolean;
export type ControlPointDestinationInRangeApiArg = {
  cpId: string;
  lat: number;
  lng: number;
};
export type SetControlPointDestinationApiResponse =
  /** status 204 Successful Response */ void;
export type SetControlPointDestinationApiArg = {
  cpId: string;
  leafletPoint: LatLng;
};
export type ClearControlPointDestinationApiResponse =
  /** status 204 Successful Response */ void;
export type ClearControlPointDestinationApiArg = {
  cpId: string;
};
export type GetDebugHoldZonesApiResponse =
  /** status 200 Successful Response */ HoldZones;
export type GetDebugHoldZonesApiArg = {
  flightId: string;
};
export type GetDebugJoinZonesApiResponse =
  /** status 200 Successful Response */ JoinZones;
export type GetDebugJoinZonesApiArg = {
  flightId: string;
};
export type ListDownedPilotsApiResponse =
  /** status 200 Successful Response */ DownedPilot[];
export type ListDownedPilotsApiArg = void;
export type GetDownedPilotByIdApiResponse =
  /** status 200 Successful Response */ DownedPilot;
export type GetDownedPilotByIdApiArg = {
  pilotId: string;
};
export type ListFlightsApiResponse =
  /** status 200 Successful Response */ Flight[];
export type ListFlightsApiArg = {
  withWaypoints?: boolean;
};
export type GetFlightByIdApiResponse =
  /** status 200 Successful Response */ Flight;
export type GetFlightByIdApiArg = {
  flightId: string;
  withWaypoints?: boolean;
};
export type GetCommitBoundaryForFlightApiResponse =
  /** status 200 Successful Response */ LatLng[][];
export type GetCommitBoundaryForFlightApiArg = {
  flightId: string;
};
export type ListFrontLinesApiResponse =
  /** status 200 Successful Response */ FrontLine[];
export type ListFrontLinesApiArg = void;
export type GetFrontLineByIdApiResponse =
  /** status 200 Successful Response */ FrontLine;
export type GetFrontLineByIdApiArg = {
  frontLineId: string;
};
export type GetGameStateApiResponse =
  /** status 200 Successful Response */ Game;
export type GetGameStateApiArg = void;
export type GetTopBarApiResponse =
  /** status 200 Successful Response */ TopBar | null;
export type GetTopBarApiArg = void;
export type GetTimelineApiResponse =
  /** status 200 Successful Response */ Timeline | null;
export type GetTimelineApiArg = void;
export type PassTurnApiResponse = /** status 200 Successful Response */ Turn;
export type PassTurnApiArg = void;
export type GetMissionChecksApiResponse =
  /** status 200 Successful Response */ MissionChecks;
export type GetMissionChecksApiArg = void;
export type FixTotsApiResponse =
  /** status 200 Successful Response */ FixedTots;
export type FixTotsApiArg = void;
export type GenerateMissionApiResponse =
  /** status 200 Successful Response */ Mission;
export type GenerateMissionApiArg = void;
export type SetSimSpeedApiResponse = /** status 200 Successful Response */ Sim;
export type SetSimSpeedApiArg = {
  simSpeedChangeJs: SimSpeedChange;
};
export type GetSettingsApiResponse =
  /** status 200 Successful Response */ Settings;
export type GetSettingsApiArg = void;
export type SetSettingApiResponse =
  /** status 200 Successful Response */ Setting;
export type SetSettingApiArg = {
  key: string;
  settingValueUpdateJs: SettingValueUpdate;
};
export type ResetSettingsPageApiResponse =
  /** status 200 Successful Response */ SettingsPage;
export type ResetSettingsPageApiArg = {
  pageId: string;
};
export type GetTerrainZonesApiResponse =
  /** status 200 Successful Response */ MapZones;
export type GetTerrainZonesApiArg = void;
export type GetOfflineBasemapImageApiResponse =
  /** status 200 Successful Response */ Blob;
export type GetOfflineBasemapImageApiArg = {
  sea?: string;
  land?: string;
  landExcluded?: string;
  coastline?: string;
};
export type ListUnculledZonesApiResponse =
  /** status 200 Successful Response */ UnculledZone[];
export type ListUnculledZonesApiArg = void;
export type GetThreatZonesApiResponse =
  /** status 200 Successful Response */ ThreatZoneContainer;
export type GetThreatZonesApiArg = void;
export type GetMissionResultApiResponse =
  /** status 200 Successful Response */ MissionResult;
export type GetMissionResultApiArg = void;
export type GetMissionReportApiResponse =
  /** status 200 Successful Response */ Debriefing;
export type GetMissionReportApiArg = void;
export type LoadMissionResultFileApiResponse =
  /** status 200 Successful Response */ MissionResult;
export type LoadMissionResultFileApiArg = void;
export type AbortMissionApiResponse =
  /** status 204 Successful Response */ void;
export type AbortMissionApiArg = void;
export type AcceptMissionResultApiResponse =
  /** status 200 Successful Response */ Turn;
export type AcceptMissionResultApiArg = void;
export type SaveGameApiResponse =
  /** status 200 Successful Response */ FileActionResult;
export type SaveGameApiArg = void;
export type SaveGameAsApiResponse =
  /** status 200 Successful Response */ FileActionResult;
export type SaveGameAsApiArg = void;
export type OpenGameApiResponse =
  /** status 200 Successful Response */ FileActionResult;
export type OpenGameApiArg = void;
export type PickFolderApiResponse =
  /** status 200 Successful Response */ FolderPickResult;
export type PickFolderApiArg = {
  folderPickRequestJs: FolderPickRequest;
};
export type OpenNewGameWizardApiResponse = unknown;
export type OpenNewGameWizardApiArg = void;
export type OpenNativeFolderApiResponse =
  /** status 204 Successful Response */ void;
export type OpenNativeFolderApiArg = {
  folder: NativeFolder;
};
export type OpenExternalLinkApiResponse =
  /** status 204 Successful Response */ void;
export type OpenExternalLinkApiArg = {
  link: ExternalLink;
};
export type QuitApplicationApiResponse = unknown;
export type QuitApplicationApiArg = void;
export type GetNavmeshApiResponse =
  /** status 200 Successful Response */ NavMesh;
export type GetNavmeshApiArg = {
  forPlayer: Player;
};
export type ListPackagesApiResponse =
  /** status 200 Successful Response */ Package[];
export type ListPackagesApiArg = void;
export type CreatePackageApiResponse =
  /** status 204 Successful Response */ void;
export type CreatePackageApiArg = {
  newPackageJs: NewPackage;
};
export type DeletePackageApiResponse =
  /** status 204 Successful Response */ void;
export type DeletePackageApiArg = {
  packageId: string;
};
export type GetInstallPreferencesApiResponse =
  /** status 200 Successful Response */ InstallPreferencesState;
export type GetInstallPreferencesApiArg = void;
export type SetInstallPreferencesApiResponse =
  /** status 200 Successful Response */ InstallPreferencesState;
export type SetInstallPreferencesApiArg = {
  installPreferencesUpdateJs: InstallPreferencesUpdate;
};
export type OpenNewFrontLinePackageDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenNewFrontLinePackageDialogApiArg = {
  frontLineId: string;
};
export type OpenNewTgoPackageDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenNewTgoPackageDialogApiArg = {
  tgoId: string;
};
export type OpenTgoInfoDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenTgoInfoDialogApiArg = {
  tgoId: string;
};
export type OpenNewControlPointPackageDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenNewControlPointPackageDialogApiArg = {
  cpId: string;
};
export type OpenNewDownedPilotPackageDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenNewDownedPilotPackageDialogApiArg = {
  pilotId: string;
};
export type SelectFlightApiResponse = /** status 200 Successful Response */ any;
export type SelectFlightApiArg = {
  flightId: string;
};
export type OpenControlPointInfoDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenControlPointInfoDialogApiArg = {
  cpId: string;
};
export type OpenQtDialogApiResponse =
  /** status 204 Successful Response */ void;
export type OpenQtDialogApiArg = {
  dialog: QtDialog;
};
export type OpenEditPackageDialogApiResponse =
  /** status 204 Successful Response */ void;
export type OpenEditPackageDialogApiArg = {
  flightId: string;
};
export type GetIntelReportApiResponse =
  /** status 200 Successful Response */ IntelJs | null;
export type GetIntelReportApiArg = void;
export type GetStatsReportApiResponse =
  /** status 200 Successful Response */ StatsJs | null;
export type GetStatsReportApiArg = void;
export type GetFinancesReportApiResponse =
  /** status 200 Successful Response */ FinancesJs | null;
export type GetFinancesReportApiArg = void;
export type ListSupplyRoutesApiResponse =
  /** status 200 Successful Response */ SupplyRoute[];
export type ListSupplyRoutesApiArg = void;
export type ListTgosApiResponse = /** status 200 Successful Response */ Tgo[];
export type ListTgosApiArg = void;
export type GetTgoByIdApiResponse = /** status 200 Successful Response */ Tgo;
export type GetTgoByIdApiArg = {
  tgoId: string;
};
export type GetTgoSummaryApiResponse =
  /** status 200 Successful Response */ TgoSummary;
export type GetTgoSummaryApiArg = {
  tgoId: string;
};
export type TgoDestinationInRangeApiResponse =
  /** status 200 Successful Response */ boolean;
export type TgoDestinationInRangeApiArg = {
  tgoId: string;
  lat: number;
  lng: number;
};
export type SetTgoDestinationApiResponse =
  /** status 204 Successful Response */ void;
export type SetTgoDestinationApiArg = {
  tgoId: string;
  leafletPoint: LatLng;
};
export type ClearTgoDestinationApiResponse =
  /** status 204 Successful Response */ void;
export type ClearTgoDestinationApiArg = {
  tgoId: string;
};
export type ListAllWaypointsForFlightApiResponse =
  /** status 200 Successful Response */ Waypoint[];
export type ListAllWaypointsForFlightApiArg = {
  flightId: string;
};
export type SetWaypointPositionApiResponse =
  /** status 204 Successful Response */ void;
export type SetWaypointPositionApiArg = {
  flightId: string;
  waypointIdx: number;
  leafletPoint: LatLng;
};
export type GetIadsNetworkApiResponse =
  /** status 200 Successful Response */ IadsNetwork;
export type GetIadsNetworkApiArg = void;
export type GetIadsConnectionsForTgoApiResponse =
  /** status 200 Successful Response */ IadsConnection[];
export type GetIadsConnectionsForTgoApiArg = {
  tgoId: string;
};
export type GetLogsApiResponse =
  /** status 200 Successful Response */ LogTailJs;
export type GetLogsApiArg = {
  lines?: number;
};
export type GetAboutApiResponse = /** status 200 Successful Response */ AboutJs;
export type GetAboutApiArg = void;
export type ListCareersApiResponse = /** status 200 Successful Response */
  | CareerJs[]
  | null;
export type ListCareersApiArg = void;
export type GetNotesApiResponse =
  /** status 200 Successful Response */ NotesJs | null;
export type GetNotesApiArg = void;
export type SetNotesApiResponse = /** status 200 Successful Response */ NotesJs;
export type SetNotesApiArg = {
  notesJs: NotesJs;
};
export type ListInformationsApiResponse = /** status 200 Successful Response */
  | InformationJs[]
  | null;
export type ListInformationsApiArg = void;
export type ImportLayoutsApiResponse =
  /** status 200 Successful Response */ LayoutImportJs;
export type ImportLayoutsApiArg = void;
export type GeneratePretenseCampaignApiResponse =
  /** status 200 Successful Response */ PretenseCampaignJs;
export type GeneratePretenseCampaignApiArg = void;
export type ListTransfersApiResponse = /** status 200 Successful Response */
  | TransferJs[]
  | null;
export type ListTransfersApiArg = void;
export type CancelTransferApiResponse =
  /** status 204 Successful Response */ void;
export type CancelTransferApiArg = {
  transferId: string;
};
export type LatLng = {
  lat: number;
  lng: number;
};
export type ControlPoint = {
  id: string;
  name: string;
  blue: boolean;
  position: LatLng;
  mobile: boolean;
  destination?: LatLng;
  sidc: string;
  cut_off?: boolean;
};
export type ValidationError = {
  loc: (string | number)[];
  msg: string;
  type: string;
};
export type HttpValidationError = {
  detail?: ValidationError[];
};
export type Runway = {
  state: "operational" | "damaged" | "repairing";
  repair_turns_remaining?: number;
};
export type Count = {
  current: number;
  total: number;
};
export type ControlPointSummary = {
  id: string;
  name: string;
  blue: boolean;
  sidc: string;
  category: string;
  distance_to_front_nm?: number;
  runway?: Runway;
  parking?: Count;
  ground_units?: Count;
  ammo_depots: Count;
  fuel_depots: Count;
  can_buy_aircraft: boolean;
  can_buy_ground_units: boolean;
  can_repair_runway: boolean;
  can_afford_runway_repair: boolean;
  runway_repair_cost: number;
};
export type BaseTab = {
  id: "airfield" | "ground-forces" | "intel" | "convoys";
  label: string;
};
export type AirDefense = {
  id: string;
  name: string;
  category: string;
  units: Count;
  operational: boolean;
};
export type Repair = {
  id: string;
  kind: "runway" | "buildings" | "aircraft";
  label: string;
  cost: number;
  turns: number;
  in_progress: boolean;
  affordable: boolean;
};
export type UnitCountJs = {
  name: string;
  count: number;
};
export type IntelGroup = {
  title: string;
  units: UnitCountJs[];
};
export type SquadronOrderRow = {
  squadron_id: string;
  squadron: string;
  aircraft: string;
  unit_cost: number;
  owned: number;
  max_aircraft?: number;
  pending: number;
  max_add: number;
  max_remove: number;
};
export type IncomingSquadron = {
  squadron: string;
  aircraft: string;
  owned: number;
  origin: string;
};
export type Airfield = {
  squadrons: SquadronOrderRow[];
  parking_after_delivery: Count;
  incoming: IncomingSquadron[];
};
export type Base = {
  summary: ControlPointSummary;
  budget: number;
  tabs: BaseTab[];
  air_defenses: AirDefense[];
  repairs: Repair[];
  repair_all_cost: number;
  repair_all_affordable: boolean;
  intel: IntelGroup[];
  airfield: Airfield;
};
export type CommandError = {
  detail: string;
};
export type AircraftOrderLine = {
  squadron_id: string;
  quantity: number;
};
export type AircraftOrders = {
  orders: AircraftOrderLine[];
};
export type SquadronPreset = {
  name: string;
  label: string;
};
export type SquadronChoice = {
  aircraft: string;
  display_name: string;
  tasks: string[];
  presets: SquadronPreset[];
};
export type NewSquadron = {
  aircraft: string;
  primary_task: string;
  preset?: string | null;
};
export type HoldZones = {
  homeBubble: LatLng[][];
  targetBubble: LatLng[][];
  joinBubble: LatLng[][];
  excludedZones: LatLng[][][];
  permissibleZones: LatLng[][][];
  preferredLines: LatLng[][];
};
export type JoinZones = {
  homeBubble: LatLng[][];
  targetBubble: LatLng[][];
  ipBubble: LatLng[][];
  excludedZones: LatLng[][][];
  permissibleZones: LatLng[][][];
  preferredLines: LatLng[][];
};
export type DownedPilot = {
  id: string;
  name: string;
  squadron: string;
  aircraft: string;
  blue: boolean;
  position: LatLng;
  turns_remaining: number;
  sidc: string;
};
export type Waypoint = {
  name: string;
  position: LatLng;
  altitude_ft: number;
  altitude_reference: string;
  is_movable: boolean;
  should_mark: boolean;
  include_in_path: boolean;
  timing: string;
};
export type Flight = {
  id: string;
  blue: boolean;
  position?: LatLng;
  sidc: string;
  waypoints?: Waypoint[];
};
export type FrontLine = {
  id: string;
  extents: LatLng[];
};
export type Tgo = {
  id: string;
  name: string;
  control_point_name: string;
  category: string;
  blue: boolean;
  position: LatLng;
  units: string[];
  threat_ranges: number[];
  detection_ranges: number[];
  dead: boolean;
  sidc: string;
  task?: string[];
  mobile: boolean;
  destination?: LatLng;
};
export type SupplyRoute = {
  id: string;
  points: LatLng[];
  front_active: boolean;
  is_sea: boolean;
  blue: boolean;
  active_transports: string[];
};
export type IadsConnection = {
  id: string;
  points: LatLng[];
  node: string;
  connected: string;
  active: boolean;
  blue: boolean;
  is_power: boolean;
};
export type IadsNetwork = {
  advanced: boolean;
  connections: IadsConnection[];
};
export type ThreatZones = {
  full: LatLng[][][];
  aircraft: LatLng[][][];
  air_defenses: LatLng[][][];
  radar_sams: LatLng[][][];
};
export type ThreatZoneContainer = {
  blue: ThreatZones;
  red: ThreatZones;
};
export type NavMeshPoly = {
  poly: LatLng[][];
  threatened: boolean;
};
export type NavMesh = {
  polys: NavMeshPoly[];
};
export type NavMeshes = {
  blue: NavMesh;
  red: NavMesh;
};
export type UnculledZone = {
  position: LatLng;
  radius: number;
};
export type OfflineBasemapImage = {
  south_west: LatLng;
  north_east: LatLng;
};
export type MapZones = {
  inclusion: LatLng[][][];
  exclusion: LatLng[][][];
  sea: LatLng[][][];
  offline_image?: OfflineBasemapImage | null;
};
export type Game = {
  control_points: ControlPoint[];
  tgos: Tgo[];
  downed_pilots: DownedPilot[];
  supply_routes: SupplyRoute[];
  front_lines: FrontLine[];
  flights: Flight[];
  iads_network: IadsNetwork;
  threat_zones: ThreatZoneContainer;
  navmeshes: NavMeshes;
  map_center?: LatLng;
  unculled_zones: UnculledZone[];
  map_zones: MapZones;
};
export type Wind = {
  altitude: string;
  direction: number;
  speed_kt: number;
};
export type Weather = {
  clouds: string;
  precipitation: string;
  fog: string;
  cloud_base_m?: number;
  cloud_base_ft?: number;
  winds: Wind[];
};
export type ForceBalance = {
  friendly: number;
  enemy: number;
  assessment: string;
};
export type SimSpeedJs =
  | "paused"
  | "1x"
  | "2x"
  | "5x"
  | "10x"
  | "100x"
  | "1000x";
export type Sim = {
  speed: SimSpeedJs;
  time?: string;
};
export type TopBar = {
  campaign_name?: string;
  theater: string;
  player_faction: string;
  enemy_faction: string;
  turn: number;
  mission_start_date: string;
  mission_start_time: string;
  time_of_day: string;
  weather: Weather;
  budget: number;
  income: number;
  air: ForceBalance;
  ground: ForceBalance;
  economy: string;
  max_player_count: number;
  sim: Sim;
  show_sim_speed_controls: boolean;
};
export type TimelinePackage = {
  id: string;
  task: string;
  target: string;
  startup: number;
  tot: number;
  landing: number;
  flight_ids: string[];
};
export type Timeline = {
  start_time: string;
  packages: TimelinePackage[];
};
export type CampaignStateJs = "continue" | "win" | "loss";
export type Turn = {
  turn: number;
  campaign_state: CampaignStateJs;
};
export type MissionChecks = {
  has_player_pilots: boolean;
  flights_missing_pilots: string[];
  packages_starting_in_the_past: string[];
  max_player_count: number;
};
export type FixedTots = {
  packages: string[];
};
export type Mission = {
  path: string;
};
export type SimSpeedChange = {
  speed: SimSpeedJs;
};
export type SettingKindJs = "bool" | "choice" | "int" | "float" | "minutes";
export type Setting = {
  key: string;
  label: string;
  detail?: string;
  tooltip?: string;
  kind: SettingKindJs;
  value: boolean | number | number | string;
  default: boolean | number | number | string;
  modified: boolean;
  min?: number;
  max?: number;
  step?: number;
  choices?: string[];
};
export type SettingsSection = {
  name: string;
  description?: string;
  settings: Setting[];
};
export type SettingsPage = {
  id: string;
  name: string;
  sections: SettingsSection[];
};
export type Settings = {
  pages: SettingsPage[];
};
export type SettingValueUpdate = {
  value: boolean | number | number | string;
};
export type MissionResultStatusJs = "idle" | "waiting" | "detected" | "error";
export type LossRow = {
  label: string;
  blue: number;
  red: number;
};
export type MissionResult = {
  status: MissionResultStatusJs;
  miz_path?: string;
  state_path: string;
  mission_ended: boolean;
  error?: string;
  player_country?: string;
  enemy_country?: string;
  losses: LossRow[];
};
export type DebriefingStatusJs = "none" | "pending" | "accepted";
export type ToneJs = "good" | "bad" | "mixed" | "neutral";
export type PilotLine = {
  name: string;
  aircraft: string;
  squadron: string;
  held_at?: string;
};
export type PackageResult = {
  task: string;
  target: string;
  flights: string[];
  lost: number;
  aircraft: number;
  result: string;
  tone: ToneJs;
};
export type LossLine = {
  name: string;
  count: number;
};
export type DamagedUnitLine = {
  friendly: boolean;
  unit_type: string;
  damage_percent: number;
  unavailability: string;
};
export type ReportEvent = {
  time?: string;
  text: string;
  tone: ToneJs;
};
export type AfterActionReport = {
  turn: number;
  date: string;
  player_country: string;
  enemy_country: string;
  verdict: string;
  verdict_tone: ToneJs;
  summary: string;
  air_kills_friendly: number;
  air_kills_enemy: number;
  ground_kills_friendly: number;
  ground_kills_enemy: number;
  bases_captured: number;
  bases_lost: number;
  pilots_rescued: PilotLine[];
  rescue_bounty: number;
  packages: PackageResult[];
  friendly_losses: LossLine[];
  enemy_losses: LossLine[];
  damaged_units: DamagedUnitLine[];
  events: ReportEvent[];
  applied: boolean;
  pilots_captured?: PilotLine[];
  pilots_still_down?: number;
  budget_next_turn?: number;
  income_next_turn?: number;
};
export type Debriefing = {
  status: DebriefingStatusJs;
  can_accept: boolean;
  report?: AfterActionReport;
};
export type FileOutcome = "saved" | "opened" | "cancelled";
export type FileActionResult = {
  outcome: FileOutcome;
  path?: string;
};
export type FolderPickResult = {
  path?: string;
};
export type FolderPurpose = "saved-games" | "dcs-install";
export type FolderPickRequest = {
  purpose: FolderPurpose;
  start?: string;
};
export type NativeFolder = "saves" | "missions";
export type ExternalLink =
  | "discord"
  | "github"
  | "ukraine"
  | "pretense-discord"
  | "releases"
  | "manual"
  | "forum-thread"
  | "issues";
export type Player = "Neutral" | "Blue" | "Red";
export type PackageFlight = {
  id: string;
  task: string;
  aircraft: string;
  count: number;
  clients: number;
  missing_pilots: number;
  squadron: string;
  departure: string;
  custom_name?: string;
};
export type Package = {
  id: string;
  blue: boolean;
  task?: string;
  description: string;
  custom_name?: string;
  target: string;
  tot?: string;
  auto_asap: boolean;
  flights: PackageFlight[];
  missing_pilots: number;
};
export type PackageTargetKind =
  | "control-point"
  | "tgo"
  | "front-line"
  | "downed-pilot";
export type NewPackage = {
  target_kind: PackageTargetKind;
  target_id: string;
};
export type InstallPreferences = {
  saved_game_dir: string;
  dcs_install_dir: string;
  prefer_liberation_payloads: boolean;
  setup_preferences_on_every_start: boolean;
  server_port: number;
  web_ui: boolean;
};
export type InstallPreferencesState = {
  preferences: InstallPreferences;
  first_start: boolean;
  saved_game_dir_problem?: string;
  dcs_install_dir_problem?: string;
  warning?: string | null;
};
export type InstallPreferencesUpdate = {
  saved_game_dir: string;
  dcs_install_dir: string;
  prefer_liberation_payloads: boolean;
  setup_preferences_on_every_start: boolean;
  server_port: number;
  web_ui: boolean;
  allow_empty_install_dir?: boolean;
};
export type QtDialog = "air-wing";
export type BaseForcesJs = {
  id: string;
  name: string;
  total: number;
  units: UnitCountJs[];
};
export type ForcesJs = {
  total: number;
  bases: BaseForcesJs[];
};
export type CoalitionIntelJs = {
  aircraft: ForcesJs;
  ground: ForcesJs;
};
export type IntelJs = {
  friendly: CoalitionIntelJs;
  enemy: CoalitionIntelJs;
};
export type TurnStatsJs = {
  turn: number;
  friendly_aircraft: number;
  enemy_aircraft: number;
  friendly_vehicles: number;
  enemy_vehicles: number;
};
export type StatsJs = {
  turns: TurnStatsJs[];
};
export type BaseIncomeJs = {
  id: string;
  name: string;
  income: number;
};
export type BuildingIncomeJs = {
  name: string;
  category: string;
  count: number;
  income_per_building: number;
  income: number;
};
export type CoalitionFinancesJs = {
  budget: number;
  multiplier: number;
  from_bases: number;
  from_buildings: number;
  total: number;
  bases: BaseIncomeJs[];
  buildings: BuildingIncomeJs[];
};
export type FinancesJs = {
  friendly: CoalitionFinancesJs;
  enemy: CoalitionFinancesJs;
};
export type TgoSummary = {
  id: string;
  name: string;
  blue: boolean;
  sidc: string;
  category: string;
  control_point_id: string;
  control_point_name: string;
  distance_to_front_nm?: number;
  units: Count;
  dead: boolean;
};
export type LogTailJs = {
  lines: string[];
  total: number;
  available: boolean;
};
export type ThanksJs = {
  name: string;
  reason: string;
};
export type AttributionJs = {
  text: string;
  url: string;
};
export type AboutJs = {
  version: string;
  source_url: string;
  authors: string;
  contributors: string[];
  special_thanks: ThanksJs[];
  attributions: AttributionJs[];
};
export type CareerTotalJs = {
  label: string;
  value: string;
};
export type AwardJs = {
  name: string;
  kind: string;
  date: string;
  turn: number;
  description: string;
};
export type LogbookEntryJs = {
  turn: number;
  date: string;
  squadron: string;
  aircraft: string;
  task: string;
  combat: boolean;
  flight_time: string;
  air_kills: number;
  ground_kills: number;
  naval_kills: number;
  rescues: number;
  loss: string;
};
export type CareerJs = {
  pilot: string;
  squadron: string;
  status: string;
  alive: boolean;
  rank?: string;
  totals: CareerTotalJs[];
  awards: AwardJs[];
  history: LogbookEntryJs[];
};
export type NotesJs = {
  text: string;
};
export type InformationJs = {
  turn: number;
  title: string;
  text: string;
  timestamp?: string;
};
export type LayoutImportJs = {
  count: number;
};
export type PretenseCampaignJs = {
  path: string;
};
export type TransferUnitJs = {
  name: string;
  count: number;
};
export type TransferJs = {
  id: string;
  origin: string;
  destination: string;
  position: string;
  size: number;
  units: TransferUnitJs[];
  transport: string;
};
export const {
  useListControlPointsQuery,
  useGetControlPointByIdQuery,
  useGetControlPointSummaryQuery,
  useGetBaseQuery,
  useOrderRepairMutation,
  useOrderAllRepairsMutation,
  useOrderAircraftMutation,
  useCancelAircraftOrderMutation,
  useGetSquadronChoicesQuery,
  useCreateSquadronMutation,
  useControlPointDestinationInRangeQuery,
  useSetControlPointDestinationMutation,
  useClearControlPointDestinationMutation,
  useGetDebugHoldZonesQuery,
  useGetDebugJoinZonesQuery,
  useListDownedPilotsQuery,
  useGetDownedPilotByIdQuery,
  useListFlightsQuery,
  useGetFlightByIdQuery,
  useGetCommitBoundaryForFlightQuery,
  useListFrontLinesQuery,
  useGetFrontLineByIdQuery,
  useGetGameStateQuery,
  useGetTopBarQuery,
  useGetTimelineQuery,
  usePassTurnMutation,
  useGetMissionChecksQuery,
  useFixTotsMutation,
  useGenerateMissionMutation,
  useSetSimSpeedMutation,
  useGetSettingsQuery,
  useSetSettingMutation,
  useResetSettingsPageMutation,
  useGetTerrainZonesQuery,
  useGetOfflineBasemapImageQuery,
  useListUnculledZonesQuery,
  useGetThreatZonesQuery,
  useGetMissionResultQuery,
  useGetMissionReportQuery,
  useLoadMissionResultFileMutation,
  useAbortMissionMutation,
  useAcceptMissionResultMutation,
  useSaveGameMutation,
  useSaveGameAsMutation,
  useOpenGameMutation,
  usePickFolderMutation,
  useOpenNewGameWizardMutation,
  useOpenNativeFolderMutation,
  useOpenExternalLinkMutation,
  useQuitApplicationMutation,
  useGetNavmeshQuery,
  useListPackagesQuery,
  useCreatePackageMutation,
  useDeletePackageMutation,
  useGetInstallPreferencesQuery,
  useSetInstallPreferencesMutation,
  useOpenNewFrontLinePackageDialogMutation,
  useOpenNewTgoPackageDialogMutation,
  useOpenTgoInfoDialogMutation,
  useOpenNewControlPointPackageDialogMutation,
  useOpenNewDownedPilotPackageDialogMutation,
  useSelectFlightMutation,
  useOpenControlPointInfoDialogMutation,
  useOpenQtDialogMutation,
  useOpenEditPackageDialogMutation,
  useGetIntelReportQuery,
  useGetStatsReportQuery,
  useGetFinancesReportQuery,
  useListSupplyRoutesQuery,
  useListTgosQuery,
  useGetTgoByIdQuery,
  useGetTgoSummaryQuery,
  useTgoDestinationInRangeQuery,
  useSetTgoDestinationMutation,
  useClearTgoDestinationMutation,
  useListAllWaypointsForFlightQuery,
  useSetWaypointPositionMutation,
  useGetIadsNetworkQuery,
  useGetIadsConnectionsForTgoQuery,
  useGetLogsQuery,
  useGetAboutQuery,
  useListCareersQuery,
  useGetNotesQuery,
  useSetNotesMutation,
  useListInformationsQuery,
  useImportLayoutsMutation,
  useGeneratePretenseCampaignMutation,
  useListTransfersQuery,
  useCancelTransferMutation,
} = injectedRtkApi;
