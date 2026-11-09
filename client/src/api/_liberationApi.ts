import { baseApi as api } from "./baseApi";
const injectedRtkApi = api.injectEndpoints({
  endpoints: (build) => ({
    getAirWing: build.query<GetAirWingApiResponse, GetAirWingApiArg>({
      query: (queryArg) => ({
        url: `/air-wing`,
        params: { enemy: queryArg.enemy },
      }),
    }),
    setSquadronPrimaryTask: build.mutation<
      SetSquadronPrimaryTaskApiResponse,
      SetSquadronPrimaryTaskApiArg
    >({
      query: (queryArg) => ({
        url: `/squadrons/${queryArg.squadronId}/primary-task`,
        method: "PUT",
        body: queryArg.primaryTaskJs,
      }),
    }),
    setSquadronAutoAssign: build.mutation<
      SetSquadronAutoAssignApiResponse,
      SetSquadronAutoAssignApiArg
    >({
      query: (queryArg) => ({
        url: `/squadrons/${queryArg.squadronId}/auto-assign`,
        method: "PUT",
        body: queryArg.autoAssignJs,
      }),
    }),
    getSquadronLiveries: build.query<
      GetSquadronLiveriesApiResponse,
      GetSquadronLiveriesApiArg
    >({
      query: (queryArg) => ({
        url: `/squadrons/${queryArg.squadronId}/liveries`,
      }),
    }),
    setSquadronLivery: build.mutation<
      SetSquadronLiveryApiResponse,
      SetSquadronLiveryApiArg
    >({
      query: (queryArg) => ({
        url: `/squadrons/${queryArg.squadronId}/livery`,
        method: "PUT",
        body: queryArg.setLiveryJs,
      }),
    }),
    getSquadronDestinations: build.query<
      GetSquadronDestinationsApiResponse,
      GetSquadronDestinationsApiArg
    >({
      query: (queryArg) => ({
        url: `/squadrons/${queryArg.squadronId}/destinations`,
      }),
    }),
    setSquadronDestination: build.mutation<
      SetSquadronDestinationApiResponse,
      SetSquadronDestinationApiArg
    >({
      query: (queryArg) => ({
        url: `/squadrons/${queryArg.squadronId}/destination`,
        method: "PUT",
        body: queryArg.setDestinationJs,
      }),
    }),
    createPlayerPilot: build.mutation<
      CreatePlayerPilotApiResponse,
      CreatePlayerPilotApiArg
    >({
      query: (queryArg) => ({
        url: `/squadrons/${queryArg.squadronId}/pilots`,
        method: "POST",
        body: queryArg.newPilotJs,
      }),
    }),
    updatePilot: build.mutation<UpdatePilotApiResponse, UpdatePilotApiArg>({
      query: (queryArg) => ({
        url: `/squadrons/${queryArg.squadronId}/pilots/${queryArg.pilotId}`,
        method: "PATCH",
        body: queryArg.pilotUpdateJs,
      }),
    }),
    getAirWingConfig: build.query<
      GetAirWingConfigApiResponse,
      GetAirWingConfigApiArg
    >({
      query: (queryArg) => ({ url: `/air-wing-config/${queryArg.target}` }),
    }),
    updateConfigSquadron: build.mutation<
      UpdateConfigSquadronApiResponse,
      UpdateConfigSquadronApiArg
    >({
      query: (queryArg) => ({
        url: `/air-wing-config/${queryArg.target}/squadrons/${queryArg.squadronId}`,
        method: "PATCH",
        body: queryArg.squadronConfigUpdateJs,
      }),
    }),
    removeConfigSquadron: build.mutation<
      RemoveConfigSquadronApiResponse,
      RemoveConfigSquadronApiArg
    >({
      query: (queryArg) => ({
        url: `/air-wing-config/${queryArg.target}/squadrons/${queryArg.squadronId}`,
        method: "DELETE",
      }),
    }),
    setConfigSquadronAutoAssign: build.mutation<
      SetConfigSquadronAutoAssignApiResponse,
      SetConfigSquadronAutoAssignApiArg
    >({
      query: (queryArg) => ({
        url: `/air-wing-config/${queryArg.target}/squadrons/${queryArg.squadronId}/auto-assign`,
        method: "PUT",
        body: queryArg.autoAssignJs,
      }),
    }),
    getConfigSquadronLiveries: build.query<
      GetConfigSquadronLiveriesApiResponse,
      GetConfigSquadronLiveriesApiArg
    >({
      query: (queryArg) => ({
        url: `/air-wing-config/${queryArg.target}/squadrons/${queryArg.squadronId}/liveries`,
      }),
    }),
    setConfigSquadronLivery: build.mutation<
      SetConfigSquadronLiveryApiResponse,
      SetConfigSquadronLiveryApiArg
    >({
      query: (queryArg) => ({
        url: `/air-wing-config/${queryArg.target}/squadrons/${queryArg.squadronId}/livery`,
        method: "PUT",
        body: queryArg.setLiveryJs,
      }),
    }),
    rerollConfigSquadronNickname: build.mutation<
      RerollConfigSquadronNicknameApiResponse,
      RerollConfigSquadronNicknameApiArg
    >({
      query: (queryArg) => ({
        url: `/air-wing-config/${queryArg.target}/squadrons/${queryArg.squadronId}/reroll-nickname`,
        method: "POST",
      }),
    }),
    replaceConfigSquadron: build.mutation<
      ReplaceConfigSquadronApiResponse,
      ReplaceConfigSquadronApiArg
    >({
      query: (queryArg) => ({
        url: `/air-wing-config/${queryArg.target}/squadrons/${queryArg.squadronId}/preset`,
        method: "POST",
        body: queryArg.replacePresetJs,
      }),
    }),
    addConfigSquadron: build.mutation<
      AddConfigSquadronApiResponse,
      AddConfigSquadronApiArg
    >({
      query: (queryArg) => ({
        url: `/air-wing-config/${queryArg.target}/sides/${queryArg.side}/squadrons`,
        method: "POST",
        body: queryArg.configNewSquadronJs,
      }),
    }),
    removeConfigAircraftSquadrons: build.mutation<
      RemoveConfigAircraftSquadronsApiResponse,
      RemoveConfigAircraftSquadronsApiArg
    >({
      query: (queryArg) => ({
        url: `/air-wing-config/${queryArg.target}/sides/${queryArg.side}/squadrons/remove-aircraft`,
        method: "POST",
        body: queryArg.configRemoveAircraftJs,
      }),
    }),
    saveAirWingFile: build.mutation<
      SaveAirWingFileApiResponse,
      SaveAirWingFileApiArg
    >({
      query: (queryArg) => ({
        url: `/air-wing-config/${queryArg.target}/sides/${queryArg.side}/file/save`,
        method: "POST",
      }),
    }),
    loadAirWingFile: build.mutation<
      LoadAirWingFileApiResponse,
      LoadAirWingFileApiArg
    >({
      query: (queryArg) => ({
        url: `/air-wing-config/${queryArg.target}/sides/${queryArg.side}/file/load`,
        method: "POST",
      }),
    }),
    getConfigFaction: build.query<
      GetConfigFactionApiResponse,
      GetConfigFactionApiArg
    >({
      query: (queryArg) => ({
        url: `/air-wing-config/${queryArg.target}/sides/${queryArg.side}/faction`,
      }),
    }),
    addConfigFactionUnit: build.mutation<
      AddConfigFactionUnitApiResponse,
      AddConfigFactionUnitApiArg
    >({
      query: (queryArg) => ({
        url: `/air-wing-config/${queryArg.target}/sides/${queryArg.side}/faction/units`,
        method: "POST",
        body: queryArg.factionUnitJs,
      }),
    }),
    setConfigFactionJtac: build.mutation<
      SetConfigFactionJtacApiResponse,
      SetConfigFactionJtacApiArg
    >({
      query: (queryArg) => ({
        url: `/air-wing-config/${queryArg.target}/sides/${queryArg.side}/faction/jtac`,
        method: "PUT",
        body: queryArg.factionJtacJs,
      }),
    }),
    setConfigFactionDoctrine: build.mutation<
      SetConfigFactionDoctrineApiResponse,
      SetConfigFactionDoctrineApiArg
    >({
      query: (queryArg) => ({
        url: `/air-wing-config/${queryArg.target}/sides/${queryArg.side}/faction/doctrine`,
        method: "PUT",
        body: queryArg.factionDoctrineJs,
      }),
    }),
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
    getGroundForces: build.query<
      GetGroundForcesApiResponse,
      GetGroundForcesApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/ground-forces`,
      }),
    }),
    orderGroundUnits: build.mutation<
      OrderGroundUnitsApiResponse,
      OrderGroundUnitsApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/purchases/ground-units`,
        method: "POST",
        body: queryArg.groundOrdersJs,
      }),
    }),
    setFrontLineStance: build.mutation<
      SetFrontLineStanceApiResponse,
      SetFrontLineStanceApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/front-lines/${queryArg.enemyId}/stance`,
        method: "PUT",
        body: queryArg.stanceJs,
      }),
    }),
    getDepartingConvoys: build.query<
      GetDepartingConvoysApiResponse,
      GetDepartingConvoysApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/convoys`,
      }),
    }),
    attackDepartingConvoy: build.mutation<
      AttackDepartingConvoyApiResponse,
      AttackDepartingConvoyApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/convoys/${queryArg.destinationId}/package`,
        method: "POST",
        params: { kind: queryArg.kind },
      }),
    }),
    getTransferOptions: build.query<
      GetTransferOptionsApiResponse,
      GetTransferOptionsApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/transfer-options`,
        params: { destination_id: queryArg.destinationId },
      }),
    }),
    getBaseActions: build.query<
      GetBaseActionsApiResponse,
      GetBaseActionsApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/actions`,
      }),
    }),
    setBaseRadios: build.mutation<
      SetBaseRadiosApiResponse,
      SetBaseRadiosApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/radios`,
        method: "PUT",
        body: queryArg.baseRadiosUpdateJs,
      }),
    }),
    cheatMoveFrontLine: build.mutation<
      CheatMoveFrontLineApiResponse,
      CheatMoveFrontLineApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/front-lines/${queryArg.enemyId}/cheat`,
        method: "POST",
        body: queryArg.frontLineCheatJs,
      }),
    }),
    cheatRunwayState: build.mutation<
      CheatRunwayStateApiResponse,
      CheatRunwayStateApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/cheat/runway`,
        method: "POST",
      }),
    }),
    cheatCaptureBase: build.mutation<
      CheatCaptureBaseApiResponse,
      CheatCaptureBaseApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/cheat/capture`,
        method: "POST",
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
    getFlightRoute: build.query<
      GetFlightRouteApiResponse,
      GetFlightRouteApiArg
    >({
      query: (queryArg) => ({ url: `/flights/${queryArg.flightId}/route` }),
    }),
    moveFlightWaypoint: build.mutation<
      MoveFlightWaypointApiResponse,
      MoveFlightWaypointApiArg
    >({
      query: (queryArg) => ({
        url: `/flights/${queryArg.flightId}/route/waypoints/${queryArg.index}/position`,
        method: "PUT",
        body: queryArg.leafletPoint,
      }),
    }),
    setFlightWaypointAltitude: build.mutation<
      SetFlightWaypointAltitudeApiResponse,
      SetFlightWaypointAltitudeApiArg
    >({
      query: (queryArg) => ({
        url: `/flights/${queryArg.flightId}/route/waypoints/${queryArg.index}/altitude`,
        method: "PUT",
        body: queryArg.waypointAltitudeJs,
      }),
    }),
    renameFlightWaypoint: build.mutation<
      RenameFlightWaypointApiResponse,
      RenameFlightWaypointApiArg
    >({
      query: (queryArg) => ({
        url: `/flights/${queryArg.flightId}/route/waypoints/${queryArg.index}/name`,
        method: "PUT",
        body: queryArg.waypointNameJs,
      }),
    }),
    deleteFlightWaypoint: build.mutation<
      DeleteFlightWaypointApiResponse,
      DeleteFlightWaypointApiArg
    >({
      query: (queryArg) => ({
        url: `/flights/${queryArg.flightId}/route/waypoints/${queryArg.index}`,
        method: "DELETE",
        params: { allow_degrade: queryArg.allowDegrade },
      }),
    }),
    insertFlightNavWaypoint: build.mutation<
      InsertFlightNavWaypointApiResponse,
      InsertFlightNavWaypointApiArg
    >({
      query: (queryArg) => ({
        url: `/flights/${queryArg.flightId}/route/waypoints/${queryArg.index}/nav`,
        method: "POST",
      }),
    }),
    addFlightRtbWaypoint: build.mutation<
      AddFlightRtbWaypointApiResponse,
      AddFlightRtbWaypointApiArg
    >({
      query: (queryArg) => ({
        url: `/flights/${queryArg.flightId}/route/rtb`,
        method: "POST",
        params: { allow_degrade: queryArg.allowDegrade },
      }),
    }),
    listPredefinedWaypoints: build.query<
      ListPredefinedWaypointsApiResponse,
      ListPredefinedWaypointsApiArg
    >({
      query: (queryArg) => ({
        url: `/flights/${queryArg.flightId}/route/predefined-waypoints`,
      }),
    }),
    addPredefinedWaypoint: build.mutation<
      AddPredefinedWaypointApiResponse,
      AddPredefinedWaypointApiArg
    >({
      query: (queryArg) => ({
        url: `/flights/${queryArg.flightId}/route/predefined-waypoints`,
        method: "POST",
        body: queryArg.newPredefinedWaypointJs,
      }),
    }),
    setFlightRouteAltitude: build.mutation<
      SetFlightRouteAltitudeApiResponse,
      SetFlightRouteAltitudeApiArg
    >({
      query: (queryArg) => ({
        url: `/flights/${queryArg.flightId}/route/altitude`,
        method: "PUT",
        body: queryArg.waypointAltitudeJs,
      }),
    }),
    recreateFlightRoute: build.mutation<
      RecreateFlightRouteApiResponse,
      RecreateFlightRouteApiArg
    >({
      query: (queryArg) => ({
        url: `/flights/${queryArg.flightId}/route/recreate`,
        method: "POST",
        body: queryArg.recreateRouteJs,
      }),
    }),
    getFlightPayload: build.query<
      GetFlightPayloadApiResponse,
      GetFlightPayloadApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/payload`,
      }),
    }),
    setFlightFuel: build.mutation<
      SetFlightFuelApiResponse,
      SetFlightFuelApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/payload/fuel`,
        method: "PUT",
        body: queryArg.flightFuelJs,
      }),
    }),
    setSameLoadout: build.mutation<
      SetSameLoadoutApiResponse,
      SetSameLoadoutApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/payload/same-loadout`,
        method: "PUT",
        body: queryArg.sameForAllJs,
      }),
    }),
    setSameLivery: build.mutation<
      SetSameLiveryApiResponse,
      SetSameLiveryApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/payload/same-livery`,
        method: "PUT",
        body: queryArg.sameForAllJs,
      }),
    }),
    backupFlightPayloads: build.mutation<
      BackupFlightPayloadsApiResponse,
      BackupFlightPayloadsApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/payload/backup`,
        method: "POST",
      }),
    }),
    setMemberLoadout: build.mutation<
      SetMemberLoadoutApiResponse,
      SetMemberLoadoutApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/payload/members/${queryArg.memberIndex}/loadout`,
        method: "PUT",
        body: queryArg.memberLoadoutNameJs,
      }),
    }),
    setMemberCustomLoadout: build.mutation<
      SetMemberCustomLoadoutApiResponse,
      SetMemberCustomLoadoutApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/payload/members/${queryArg.memberIndex}/custom`,
        method: "PUT",
        body: queryArg.memberCustomLoadoutJs,
      }),
    }),
    setMemberPylon: build.mutation<
      SetMemberPylonApiResponse,
      SetMemberPylonApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/payload/members/${queryArg.memberIndex}/pylons/${queryArg["number"]}`,
        method: "PUT",
        body: queryArg.memberPylonWeaponJs,
      }),
    }),
    setMemberWeaponSetting: build.mutation<
      SetMemberWeaponSettingApiResponse,
      SetMemberWeaponSettingApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/payload/members/${queryArg.memberIndex}/pylons/${queryArg["number"]}/settings`,
        method: "PUT",
        body: queryArg.payloadValueJs,
      }),
    }),
    resetMemberWeaponSettings: build.mutation<
      ResetMemberWeaponSettingsApiResponse,
      ResetMemberWeaponSettingsApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/payload/members/${queryArg.memberIndex}/pylons/${queryArg["number"]}/settings`,
        method: "DELETE",
      }),
    }),
    setMemberTgpLaserCode: build.mutation<
      SetMemberTgpLaserCodeApiResponse,
      SetMemberTgpLaserCodeApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/payload/members/${queryArg.memberIndex}/tgp-laser-code`,
        method: "PUT",
        body: queryArg.tgpLaserCodeJs,
      }),
    }),
    setMemberWeaponLaserCode: build.mutation<
      SetMemberWeaponLaserCodeApiResponse,
      SetMemberWeaponLaserCodeApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/payload/members/${queryArg.memberIndex}/weapon-laser-code`,
        method: "PUT",
        body: queryArg.weaponLaserCodeChoiceJs,
      }),
    }),
    setMemberLivery: build.mutation<
      SetMemberLiveryApiResponse,
      SetMemberLiveryApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/payload/members/${queryArg.memberIndex}/livery`,
        method: "PUT",
        body: queryArg.memberLiveryJs,
      }),
    }),
    setMemberProperty: build.mutation<
      SetMemberPropertyApiResponse,
      SetMemberPropertyApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/payload/members/${queryArg.memberIndex}/properties`,
        method: "PUT",
        body: queryArg.payloadValueJs,
      }),
    }),
    saveMemberPayload: build.mutation<
      SaveMemberPayloadApiResponse,
      SaveMemberPayloadApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/payload/members/${queryArg.memberIndex}/save`,
        method: "POST",
        body: queryArg.savePayloadJs,
      }),
    }),
    listFlights: build.query<ListFlightsApiResponse, ListFlightsApiArg>({
      query: (queryArg) => ({
        url: `/flights/`,
        params: { with_waypoints: queryArg.withWaypoints },
      }),
    }),
    selectFlight: build.mutation<SelectFlightApiResponse, SelectFlightApiArg>({
      query: (queryArg) => ({
        url: `/flights/${queryArg.flightId}/select`,
        method: "POST",
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
    getNewGameOptions: build.query<
      GetNewGameOptionsApiResponse,
      GetNewGameOptionsApiArg
    >({
      query: () => ({ url: `/new-game/options` }),
    }),
    getCampaignPreview: build.query<
      GetCampaignPreviewApiResponse,
      GetCampaignPreviewApiArg
    >({
      query: (queryArg) => ({
        url: `/new-game/campaigns/${queryArg.campaignId}/preview`,
      }),
    }),
    getCampaignDefaults: build.query<
      GetCampaignDefaultsApiResponse,
      GetCampaignDefaultsApiArg
    >({
      query: (queryArg) => ({
        url: `/new-game/campaigns/${queryArg.campaignId}/defaults`,
      }),
    }),
    getNewGameFaction: build.query<
      GetNewGameFactionApiResponse,
      GetNewGameFactionApiArg
    >({
      query: (queryArg) => ({
        url: `/new-game/faction`,
        params: { name: queryArg.name },
      }),
    }),
    saveNewGameFaction: build.mutation<
      SaveNewGameFactionApiResponse,
      SaveNewGameFactionApiArg
    >({
      query: (queryArg) => ({
        url: `/new-game/factions`,
        method: "POST",
        body: queryArg.saveFactionJs,
      }),
    }),
    getNewGameGeneration: build.query<
      GetNewGameGenerationApiResponse,
      GetNewGameGenerationApiArg
    >({
      query: () => ({ url: `/new-game/generation` }),
    }),
    startNewGameGeneration: build.mutation<
      StartNewGameGenerationApiResponse,
      StartNewGameGenerationApiArg
    >({
      query: (queryArg) => ({
        url: `/new-game/generation`,
        method: "POST",
        body: queryArg.newGameRequestJs,
      }),
    }),
    cancelNewGameGeneration: build.mutation<
      CancelNewGameGenerationApiResponse,
      CancelNewGameGenerationApiArg
    >({
      query: () => ({ url: `/new-game/generation`, method: "DELETE" }),
    }),
    beginNewGame: build.mutation<BeginNewGameApiResponse, BeginNewGameApiArg>({
      query: () => ({ url: `/new-game/generation/begin`, method: "POST" }),
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
    deletePlayerPackages: build.mutation<
      DeletePlayerPackagesApiResponse,
      DeletePlayerPackagesApiArg
    >({
      query: () => ({ url: `/packages/`, method: "DELETE" }),
    }),
    getPackage: build.query<GetPackageApiResponse, GetPackageApiArg>({
      query: (queryArg) => ({ url: `/packages/${queryArg.packageId}` }),
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
    renamePackage: build.mutation<
      RenamePackageApiResponse,
      RenamePackageApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/name`,
        method: "PUT",
        body: queryArg.packageNameJs,
      }),
    }),
    setPackageTot: build.mutation<
      SetPackageTotApiResponse,
      SetPackageTotApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/tot`,
        method: "PUT",
        body: queryArg.packageTotJs,
      }),
    }),
    setPackageTotEarliest: build.mutation<
      SetPackageTotEarliestApiResponse,
      SetPackageTotEarliestApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/tot/earliest`,
        method: "POST",
      }),
    }),
    getFlightOptions: build.query<
      GetFlightOptionsApiResponse,
      GetFlightOptionsApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flight-options`,
      }),
    }),
    addPackageFlight: build.mutation<
      AddPackageFlightApiResponse,
      AddPackageFlightApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights`,
        method: "POST",
        body: queryArg.newFlightJs,
      }),
    }),
    removePackageFlight: build.mutation<
      RemovePackageFlightApiResponse,
      RemovePackageFlightApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}`,
        method: "DELETE",
      }),
    }),
    getAutoCreateOptions: build.query<
      GetAutoCreateOptionsApiResponse,
      GetAutoCreateOptionsApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/auto-create`,
      }),
    }),
    autoCreatePackage: build.mutation<
      AutoCreatePackageApiResponse,
      AutoCreatePackageApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/auto-create`,
        method: "POST",
        body: queryArg.autoCreateRequestJs,
      }),
    }),
    getFlightSettings: build.query<
      GetFlightSettingsApiResponse,
      GetFlightSettingsApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/settings`,
      }),
    }),
    setFlightSquadron: build.mutation<
      SetFlightSquadronApiResponse,
      SetFlightSquadronApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/squadron`,
        method: "PUT",
        body: queryArg.flightSquadronChoiceJs,
      }),
    }),
    setFlightSize: build.mutation<
      SetFlightSizeApiResponse,
      SetFlightSizeApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/size`,
        method: "PUT",
        body: queryArg.flightSizeJs,
      }),
    }),
    setFlightStartType: build.mutation<
      SetFlightStartTypeApiResponse,
      SetFlightStartTypeApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/start-type`,
        method: "PUT",
        body: queryArg.flightStartTypeJs,
      }),
    }),
    setFlightDivert: build.mutation<
      SetFlightDivertApiResponse,
      SetFlightDivertApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/divert`,
        method: "PUT",
        body: queryArg.flightDivertJs,
      }),
    }),
    setFlightTotOffset: build.mutation<
      SetFlightTotOffsetApiResponse,
      SetFlightTotOffsetApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/tot-offset`,
        method: "PUT",
        body: queryArg.flightTotOffsetJs,
      }),
    }),
    setFlightCustomName: build.mutation<
      SetFlightCustomNameApiResponse,
      SetFlightCustomNameApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/custom-name`,
        method: "PUT",
        body: queryArg.flightCustomNameJs,
      }),
    }),
    setFlightCallsign: build.mutation<
      SetFlightCallsignApiResponse,
      SetFlightCallsignApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/callsign`,
        method: "PUT",
        body: queryArg.flightCallsignJs,
      }),
    }),
    resetFlightCallsign: build.mutation<
      ResetFlightCallsignApiResponse,
      ResetFlightCallsignApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/callsign`,
        method: "DELETE",
      }),
    }),
    setFlightPilot: build.mutation<
      SetFlightPilotApiResponse,
      SetFlightPilotApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/pilots/${queryArg.slot}`,
        method: "PUT",
        body: queryArg.flightPilotChoiceJs,
      }),
    }),
    setFlightSlotPlayer: build.mutation<
      SetFlightSlotPlayerApiResponse,
      SetFlightSlotPlayerApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/pilots/${queryArg.slot}/player`,
        method: "PUT",
        body: queryArg.flightSlotPlayerJs,
      }),
    }),
    getFlightRadios: build.query<
      GetFlightRadiosApiResponse,
      GetFlightRadiosApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/radios`,
      }),
    }),
    setFlightFrequency: build.mutation<
      SetFlightFrequencyApiResponse,
      SetFlightFrequencyApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/radios/frequency`,
        method: "PUT",
        body: queryArg.flightFrequencyJs,
      }),
    }),
    setPackageFrequency: build.mutation<
      SetPackageFrequencyApiResponse,
      SetPackageFrequencyApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/radios/package-frequency`,
        method: "PUT",
        body: queryArg.packageFrequencyJs,
      }),
    }),
    setFlightTacan: build.mutation<
      SetFlightTacanApiResponse,
      SetFlightTacanApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/radios/tacan`,
        method: "PUT",
        body: queryArg.flightTacanJs,
      }),
    }),
    setFlightDatalink: build.mutation<
      SetFlightDatalinkApiResponse,
      SetFlightDatalinkApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/radios/datalink/${queryArg.memberIndex}`,
        method: "PUT",
        body: queryArg.datalinkValueJs,
      }),
    }),
    saveFlightCartridge: build.mutation<
      SaveFlightCartridgeApiResponse,
      SaveFlightCartridgeApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}/flights/${queryArg.flightId}/radios/cartridge/save`,
        method: "POST",
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
    getPlayerModules: build.query<
      GetPlayerModulesApiResponse,
      GetPlayerModulesApiArg
    >({
      query: () => ({ url: `/preferences/modules` }),
    }),
    setPlayerModules: build.mutation<
      SetPlayerModulesApiResponse,
      SetPlayerModulesApiArg
    >({
      query: (queryArg) => ({
        url: `/preferences/modules`,
        method: "PUT",
        body: queryArg.ownedModulesJs,
      }),
    }),
    getProduction: build.query<GetProductionApiResponse, GetProductionApiArg>({
      query: () => ({ url: `/production/` }),
    }),
    runProductionAction: build.mutation<
      RunProductionActionApiResponse,
      RunProductionActionApiArg
    >({
      query: (queryArg) => ({
        url: `/production/items/${queryArg.itemId}/action`,
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
    listSaves: build.query<ListSavesApiResponse, ListSavesApiArg>({
      query: () => ({ url: `/saves/` }),
    }),
    loadSave: build.mutation<LoadSaveApiResponse, LoadSaveApiArg>({
      query: (queryArg) => ({
        url: `/saves/${queryArg.saveId}/load`,
        method: "POST",
      }),
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
    getTgoSheet: build.query<GetTgoSheetApiResponse, GetTgoSheetApiArg>({
      query: (queryArg) => ({ url: `/tgos/${queryArg.tgoId}/sheet` }),
    }),
    repairTgoUnit: build.mutation<
      RepairTgoUnitApiResponse,
      RepairTgoUnitApiArg
    >({
      query: (queryArg) => ({
        url: `/tgos/${queryArg.tgoId}/units/${queryArg.unitId}/repair`,
        method: "POST",
      }),
    }),
    setTgoHeading: build.mutation<
      SetTgoHeadingApiResponse,
      SetTgoHeadingApiArg
    >({
      query: (queryArg) => ({
        url: `/tgos/${queryArg.tgoId}/heading`,
        method: "PUT",
        body: queryArg.tgoHeadingChangeJs,
      }),
    }),
    setTgoHiddenOnMfd: build.mutation<
      SetTgoHiddenOnMfdApiResponse,
      SetTgoHiddenOnMfdApiArg
    >({
      query: (queryArg) => ({
        url: `/tgos/${queryArg.tgoId}/hidden-on-mfd`,
        method: "PUT",
        body: queryArg.tgoHiddenChangeJs,
      }),
    }),
    disbandTgoGroup: build.mutation<
      DisbandTgoGroupApiResponse,
      DisbandTgoGroupApiArg
    >({
      query: (queryArg) => ({
        url: `/tgos/${queryArg.tgoId}/group`,
        method: "DELETE",
      }),
    }),
    getTgoPurchaseOptions: build.query<
      GetTgoPurchaseOptionsApiResponse,
      GetTgoPurchaseOptionsApiArg
    >({
      query: (queryArg) => ({
        url: `/tgos/${queryArg.tgoId}/purchase-options`,
      }),
    }),
    quoteTgoPurchase: build.mutation<
      QuoteTgoPurchaseApiResponse,
      QuoteTgoPurchaseApiArg
    >({
      query: (queryArg) => ({
        url: `/tgos/${queryArg.tgoId}/purchase/quote`,
        method: "POST",
        body: queryArg.tgoPurchaseJs,
      }),
    }),
    buyTgoGroup: build.mutation<BuyTgoGroupApiResponse, BuyTgoGroupApiArg>({
      query: (queryArg) => ({
        url: `/tgos/${queryArg.tgoId}/purchase`,
        method: "POST",
        body: queryArg.tgoPurchaseJs,
      }),
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
    getUnitInfo: build.query<GetUnitInfoApiResponse, GetUnitInfoApiArg>({
      query: (queryArg) => ({
        url: `/unit-info`,
        params: { kind: queryArg.kind, name: queryArg.name },
      }),
    }),
    getUnitBanner: build.query<GetUnitBannerApiResponse, GetUnitBannerApiArg>({
      query: (queryArg) => ({
        url: `/unit-info/banner`,
        params: { kind: queryArg.kind, name: queryArg.name },
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
    getObjectives: build.query<GetObjectivesApiResponse, GetObjectivesApiArg>({
      query: () => ({ url: `/objectives` }),
    }),
    getWarDiary: build.query<GetWarDiaryApiResponse, GetWarDiaryApiArg>({
      query: () => ({ url: `/war-diary` }),
    }),
    exportWarDiary: build.mutation<
      ExportWarDiaryApiResponse,
      ExportWarDiaryApiArg
    >({
      query: () => ({ url: `/war-diary/export`, method: "POST" }),
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
    createTransfer: build.mutation<
      CreateTransferApiResponse,
      CreateTransferApiArg
    >({
      query: (queryArg) => ({
        url: `/transfers/`,
        method: "POST",
        body: queryArg.newTransferJs,
      }),
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
export type GetAirWingApiResponse =
  /** status 200 Successful Response */ AirWing | null;
export type GetAirWingApiArg = {
  enemy?: boolean;
};
export type SetSquadronPrimaryTaskApiResponse =
  /** status 204 Successful Response */ void;
export type SetSquadronPrimaryTaskApiArg = {
  squadronId: string;
  primaryTaskJs: PrimaryTask;
};
export type SetSquadronAutoAssignApiResponse =
  /** status 204 Successful Response */ void;
export type SetSquadronAutoAssignApiArg = {
  squadronId: string;
  autoAssignJs: AutoAssign;
};
export type GetSquadronLiveriesApiResponse =
  /** status 200 Successful Response */ LiveryChoice[];
export type GetSquadronLiveriesApiArg = {
  squadronId: string;
};
export type SetSquadronLiveryApiResponse =
  /** status 204 Successful Response */ void;
export type SetSquadronLiveryApiArg = {
  squadronId: string;
  setLiveryJs: SetLivery;
};
export type GetSquadronDestinationsApiResponse =
  /** status 200 Successful Response */ SquadronTransferOptions;
export type GetSquadronDestinationsApiArg = {
  squadronId: string;
};
export type SetSquadronDestinationApiResponse =
  /** status 204 Successful Response */ void;
export type SetSquadronDestinationApiArg = {
  squadronId: string;
  setDestinationJs: SetDestination;
};
export type CreatePlayerPilotApiResponse =
  /** status 204 Successful Response */ void;
export type CreatePlayerPilotApiArg = {
  squadronId: string;
  newPilotJs: NewPilot;
};
export type UpdatePilotApiResponse = /** status 204 Successful Response */ void;
export type UpdatePilotApiArg = {
  squadronId: string;
  pilotId: string;
  pilotUpdateJs: PilotUpdate;
};
export type GetAirWingConfigApiResponse =
  /** status 200 Successful Response */ AirWingConfig;
export type GetAirWingConfigApiArg = {
  target: ConfigTarget;
};
export type UpdateConfigSquadronApiResponse =
  /** status 204 Successful Response */ void;
export type UpdateConfigSquadronApiArg = {
  target: ConfigTarget;
  squadronId: string;
  squadronConfigUpdateJs: SquadronConfigUpdate;
};
export type RemoveConfigSquadronApiResponse =
  /** status 204 Successful Response */ void;
export type RemoveConfigSquadronApiArg = {
  target: ConfigTarget;
  squadronId: string;
};
export type SetConfigSquadronAutoAssignApiResponse =
  /** status 204 Successful Response */ void;
export type SetConfigSquadronAutoAssignApiArg = {
  squadronId: string;
  target: ConfigTarget;
  autoAssignJs: AutoAssign;
};
export type GetConfigSquadronLiveriesApiResponse =
  /** status 200 Successful Response */ LiveryChoice[];
export type GetConfigSquadronLiveriesApiArg = {
  squadronId: string;
  target: ConfigTarget;
};
export type SetConfigSquadronLiveryApiResponse =
  /** status 204 Successful Response */ void;
export type SetConfigSquadronLiveryApiArg = {
  squadronId: string;
  target: ConfigTarget;
  setLiveryJs: SetLivery;
};
export type RerollConfigSquadronNicknameApiResponse =
  /** status 204 Successful Response */ void;
export type RerollConfigSquadronNicknameApiArg = {
  squadronId: string;
  target: ConfigTarget;
};
export type ReplaceConfigSquadronApiResponse =
  /** status 204 Successful Response */ void;
export type ReplaceConfigSquadronApiArg = {
  target: ConfigTarget;
  squadronId: string;
  replacePresetJs: AirWingConfigReplacePreset;
};
export type AddConfigSquadronApiResponse =
  /** status 204 Successful Response */ void;
export type AddConfigSquadronApiArg = {
  target: ConfigTarget;
  side: ConfigSide;
  configNewSquadronJs: AirWingConfigNewSquadron;
};
export type RemoveConfigAircraftSquadronsApiResponse =
  /** status 204 Successful Response */ void;
export type RemoveConfigAircraftSquadronsApiArg = {
  target: ConfigTarget;
  side: ConfigSide;
  configRemoveAircraftJs: AirWingConfigRemoveAircraft;
};
export type SaveAirWingFileApiResponse =
  /** status 200 Successful Response */ AirWingFileResult;
export type SaveAirWingFileApiArg = {
  side: ConfigSide;
  target: ConfigTarget;
};
export type LoadAirWingFileApiResponse =
  /** status 200 Successful Response */ AirWingFileResult;
export type LoadAirWingFileApiArg = {
  target: ConfigTarget;
  side: ConfigSide;
};
export type GetConfigFactionApiResponse =
  /** status 200 Successful Response */ FactionSheet;
export type GetConfigFactionApiArg = {
  side: ConfigSide;
  target: ConfigTarget;
};
export type AddConfigFactionUnitApiResponse =
  /** status 204 Successful Response */ void;
export type AddConfigFactionUnitApiArg = {
  side: ConfigSide;
  target: ConfigTarget;
  factionUnitJs: AirWingConfigFactionUnit;
};
export type SetConfigFactionJtacApiResponse =
  /** status 204 Successful Response */ void;
export type SetConfigFactionJtacApiArg = {
  side: ConfigSide;
  target: ConfigTarget;
  factionJtacJs: AirWingConfigFactionJtac;
};
export type SetConfigFactionDoctrineApiResponse =
  /** status 204 Successful Response */ void;
export type SetConfigFactionDoctrineApiArg = {
  side: ConfigSide;
  target: ConfigTarget;
  factionDoctrineJs: AirWingConfigFactionDoctrine;
};
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
export type GetGroundForcesApiResponse =
  /** status 200 Successful Response */ GroundForces;
export type GetGroundForcesApiArg = {
  cpId: string;
};
export type OrderGroundUnitsApiResponse =
  /** status 200 Successful Response */ GroundForces;
export type OrderGroundUnitsApiArg = {
  cpId: string;
  groundOrdersJs: GroundOrders;
};
export type SetFrontLineStanceApiResponse =
  /** status 200 Successful Response */ GroundForces;
export type SetFrontLineStanceApiArg = {
  cpId: string;
  enemyId: string;
  stanceJs: Stance;
};
export type GetDepartingConvoysApiResponse =
  /** status 200 Successful Response */ DepartingConvoy[];
export type GetDepartingConvoysApiArg = {
  cpId: string;
};
export type AttackDepartingConvoyApiResponse =
  /** status 201 Successful Response */ PlannedPackage;
export type AttackDepartingConvoyApiArg = {
  cpId: string;
  destinationId: string;
  kind?: "convoy" | "cargo-ship";
};
export type GetTransferOptionsApiResponse =
  /** status 200 Successful Response */ TransferOptions;
export type GetTransferOptionsApiArg = {
  cpId: string;
  destinationId?: string | null;
};
export type GetBaseActionsApiResponse =
  /** status 200 Successful Response */ BaseActions;
export type GetBaseActionsApiArg = {
  cpId: string;
};
export type SetBaseRadiosApiResponse =
  /** status 200 Successful Response */ BaseActions;
export type SetBaseRadiosApiArg = {
  cpId: string;
  baseRadiosUpdateJs: BaseRadiosUpdate;
};
export type CheatMoveFrontLineApiResponse =
  /** status 204 Successful Response */ void;
export type CheatMoveFrontLineApiArg = {
  cpId: string;
  enemyId: string;
  frontLineCheatJs: FrontLineCheat;
};
export type CheatRunwayStateApiResponse =
  /** status 204 Successful Response */ void;
export type CheatRunwayStateApiArg = {
  cpId: string;
};
export type CheatCaptureBaseApiResponse =
  /** status 204 Successful Response */ void;
export type CheatCaptureBaseApiArg = {
  cpId: string;
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
export type GetFlightRouteApiResponse =
  /** status 200 Successful Response */ FlightRoute;
export type GetFlightRouteApiArg = {
  flightId: string;
};
export type MoveFlightWaypointApiResponse =
  /** status 200 Successful Response */ FlightRoute;
export type MoveFlightWaypointApiArg = {
  flightId: string;
  index: number;
  leafletPoint: LatLng;
};
export type SetFlightWaypointAltitudeApiResponse =
  /** status 200 Successful Response */ FlightRoute;
export type SetFlightWaypointAltitudeApiArg = {
  flightId: string;
  index: number;
  waypointAltitudeJs: WaypointAltitude;
};
export type RenameFlightWaypointApiResponse =
  /** status 200 Successful Response */ FlightRoute;
export type RenameFlightWaypointApiArg = {
  flightId: string;
  index: number;
  waypointNameJs: WaypointName;
};
export type DeleteFlightWaypointApiResponse =
  /** status 200 Successful Response */ FlightRoute;
export type DeleteFlightWaypointApiArg = {
  flightId: string;
  index: number;
  allowDegrade?: boolean;
};
export type InsertFlightNavWaypointApiResponse =
  /** status 200 Successful Response */ FlightRoute;
export type InsertFlightNavWaypointApiArg = {
  flightId: string;
  index: number;
};
export type AddFlightRtbWaypointApiResponse =
  /** status 200 Successful Response */ FlightRoute;
export type AddFlightRtbWaypointApiArg = {
  flightId: string;
  allowDegrade?: boolean;
};
export type ListPredefinedWaypointsApiResponse =
  /** status 200 Successful Response */ PredefinedWaypoint[];
export type ListPredefinedWaypointsApiArg = {
  flightId: string;
};
export type AddPredefinedWaypointApiResponse =
  /** status 200 Successful Response */ FlightRoute;
export type AddPredefinedWaypointApiArg = {
  flightId: string;
  newPredefinedWaypointJs: NewPredefinedWaypoint;
};
export type SetFlightRouteAltitudeApiResponse =
  /** status 200 Successful Response */ FlightRoute;
export type SetFlightRouteAltitudeApiArg = {
  flightId: string;
  waypointAltitudeJs: WaypointAltitude;
};
export type RecreateFlightRouteApiResponse =
  /** status 200 Successful Response */ FlightRoute;
export type RecreateFlightRouteApiArg = {
  flightId: string;
  recreateRouteJs: RecreateRoute;
};
export type GetFlightPayloadApiResponse =
  /** status 200 Successful Response */ FlightPayload;
export type GetFlightPayloadApiArg = {
  packageId: string;
  flightId: string;
};
export type SetFlightFuelApiResponse =
  /** status 200 Successful Response */ FlightPayload;
export type SetFlightFuelApiArg = {
  packageId: string;
  flightId: string;
  flightFuelJs: FlightFuel;
};
export type SetSameLoadoutApiResponse =
  /** status 200 Successful Response */ FlightPayload;
export type SetSameLoadoutApiArg = {
  packageId: string;
  flightId: string;
  sameForAllJs: SameForAll;
};
export type SetSameLiveryApiResponse =
  /** status 200 Successful Response */ FlightPayload;
export type SetSameLiveryApiArg = {
  packageId: string;
  flightId: string;
  sameForAllJs: SameForAll;
};
export type BackupFlightPayloadsApiResponse =
  /** status 200 Successful Response */ PayloadFile;
export type BackupFlightPayloadsApiArg = {
  packageId: string;
  flightId: string;
};
export type SetMemberLoadoutApiResponse =
  /** status 200 Successful Response */ FlightPayload;
export type SetMemberLoadoutApiArg = {
  packageId: string;
  flightId: string;
  memberIndex: number;
  memberLoadoutNameJs: MemberLoadoutName;
};
export type SetMemberCustomLoadoutApiResponse =
  /** status 200 Successful Response */ FlightPayload;
export type SetMemberCustomLoadoutApiArg = {
  packageId: string;
  flightId: string;
  memberIndex: number;
  memberCustomLoadoutJs: MemberCustomLoadout;
};
export type SetMemberPylonApiResponse =
  /** status 200 Successful Response */ FlightPayload;
export type SetMemberPylonApiArg = {
  packageId: string;
  flightId: string;
  memberIndex: number;
  number: number;
  memberPylonWeaponJs: MemberPylonWeapon;
};
export type SetMemberWeaponSettingApiResponse =
  /** status 200 Successful Response */ FlightPayload;
export type SetMemberWeaponSettingApiArg = {
  packageId: string;
  flightId: string;
  memberIndex: number;
  number: number;
  payloadValueJs: PayloadValue;
};
export type ResetMemberWeaponSettingsApiResponse =
  /** status 200 Successful Response */ FlightPayload;
export type ResetMemberWeaponSettingsApiArg = {
  packageId: string;
  flightId: string;
  memberIndex: number;
  number: number;
};
export type SetMemberTgpLaserCodeApiResponse =
  /** status 200 Successful Response */ FlightPayload;
export type SetMemberTgpLaserCodeApiArg = {
  packageId: string;
  flightId: string;
  memberIndex: number;
  tgpLaserCodeJs: TgpLaserCode;
};
export type SetMemberWeaponLaserCodeApiResponse =
  /** status 200 Successful Response */ FlightPayload;
export type SetMemberWeaponLaserCodeApiArg = {
  packageId: string;
  flightId: string;
  memberIndex: number;
  weaponLaserCodeChoiceJs: WeaponLaserCodeChoice;
};
export type SetMemberLiveryApiResponse =
  /** status 200 Successful Response */ FlightPayload;
export type SetMemberLiveryApiArg = {
  packageId: string;
  flightId: string;
  memberIndex: number;
  memberLiveryJs: MemberLivery;
};
export type SetMemberPropertyApiResponse =
  /** status 200 Successful Response */ FlightPayload;
export type SetMemberPropertyApiArg = {
  packageId: string;
  flightId: string;
  memberIndex: number;
  payloadValueJs: PayloadValue;
};
export type SaveMemberPayloadApiResponse =
  /** status 200 Successful Response */ PayloadFile;
export type SaveMemberPayloadApiArg = {
  packageId: string;
  flightId: string;
  memberIndex: number;
  savePayloadJs: SavePayload;
};
export type ListFlightsApiResponse =
  /** status 200 Successful Response */ Flight[];
export type ListFlightsApiArg = {
  withWaypoints?: boolean;
};
export type SelectFlightApiResponse = /** status 200 Successful Response */ any;
export type SelectFlightApiArg = {
  flightId: string;
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
  /** status 200 Successful Response */ Game | null;
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
export type GetNewGameOptionsApiResponse =
  /** status 200 Successful Response */ NewGameOptions;
export type GetNewGameOptionsApiArg = void;
export type GetCampaignPreviewApiResponse =
  /** status 200 Successful Response */ CampaignPreview;
export type GetCampaignPreviewApiArg = {
  campaignId: string;
};
export type GetCampaignDefaultsApiResponse =
  /** status 200 Successful Response */ CampaignDefaults;
export type GetCampaignDefaultsApiArg = {
  campaignId: string;
};
export type GetNewGameFactionApiResponse =
  /** status 200 Successful Response */ FactionSheet;
export type GetNewGameFactionApiArg = {
  name: string;
};
export type SaveNewGameFactionApiResponse =
  /** status 204 Successful Response */ void;
export type SaveNewGameFactionApiArg = {
  saveFactionJs: SaveFaction;
};
export type GetNewGameGenerationApiResponse =
  /** status 200 Successful Response */ NewGameGeneration;
export type GetNewGameGenerationApiArg = void;
export type StartNewGameGenerationApiResponse =
  /** status 200 Successful Response */ NewGameGeneration;
export type StartNewGameGenerationApiArg = {
  newGameRequestJs: NewGameRequest;
};
export type CancelNewGameGenerationApiResponse =
  /** status 200 Successful Response */ NewGameGeneration;
export type CancelNewGameGenerationApiArg = void;
export type BeginNewGameApiResponse =
  /** status 200 Successful Response */ NewGameGeneration;
export type BeginNewGameApiArg = void;
export type ListPackagesApiResponse =
  /** status 200 Successful Response */ Package[];
export type ListPackagesApiArg = void;
export type CreatePackageApiResponse =
  /** status 201 Successful Response */ PackageDetail;
export type CreatePackageApiArg = {
  newPackageJs: NewPackage;
};
export type DeletePlayerPackagesApiResponse =
  /** status 204 Successful Response */ void;
export type DeletePlayerPackagesApiArg = void;
export type GetPackageApiResponse =
  /** status 200 Successful Response */ PackageDetail;
export type GetPackageApiArg = {
  packageId: string;
};
export type DeletePackageApiResponse =
  /** status 204 Successful Response */ void;
export type DeletePackageApiArg = {
  packageId: string;
};
export type RenamePackageApiResponse =
  /** status 200 Successful Response */ PackageDetail;
export type RenamePackageApiArg = {
  packageId: string;
  packageNameJs: PackageName;
};
export type SetPackageTotApiResponse =
  /** status 200 Successful Response */ PackageDetail;
export type SetPackageTotApiArg = {
  packageId: string;
  packageTotJs: PackageTot;
};
export type SetPackageTotEarliestApiResponse =
  /** status 200 Successful Response */ PackageDetail;
export type SetPackageTotEarliestApiArg = {
  packageId: string;
};
export type GetFlightOptionsApiResponse =
  /** status 200 Successful Response */ FlightOptions;
export type GetFlightOptionsApiArg = {
  packageId: string;
};
export type AddPackageFlightApiResponse =
  /** status 201 Successful Response */ PackageDetail;
export type AddPackageFlightApiArg = {
  packageId: string;
  newFlightJs: NewFlight;
};
export type RemovePackageFlightApiResponse =
  /** status 200 Successful Response */ PackageDetail;
export type RemovePackageFlightApiArg = {
  packageId: string;
  flightId: string;
};
export type GetAutoCreateOptionsApiResponse =
  /** status 200 Successful Response */ AutoCreateOptions;
export type GetAutoCreateOptionsApiArg = {
  packageId: string;
};
export type AutoCreatePackageApiResponse =
  /** status 200 Successful Response */ PackageDetail;
export type AutoCreatePackageApiArg = {
  packageId: string;
  autoCreateRequestJs: AutoCreateRequest;
};
export type GetFlightSettingsApiResponse =
  /** status 200 Successful Response */ FlightSettings;
export type GetFlightSettingsApiArg = {
  packageId: string;
  flightId: string;
};
export type SetFlightSquadronApiResponse =
  /** status 200 Successful Response */ FlightSquadronChanged;
export type SetFlightSquadronApiArg = {
  packageId: string;
  flightId: string;
  flightSquadronChoiceJs: FlightSquadronChoice;
};
export type SetFlightSizeApiResponse =
  /** status 200 Successful Response */ PackageDetail;
export type SetFlightSizeApiArg = {
  packageId: string;
  flightId: string;
  flightSizeJs: FlightSize;
};
export type SetFlightStartTypeApiResponse =
  /** status 200 Successful Response */ PackageDetail;
export type SetFlightStartTypeApiArg = {
  packageId: string;
  flightId: string;
  flightStartTypeJs: FlightStartType;
};
export type SetFlightDivertApiResponse =
  /** status 200 Successful Response */ PackageDetail;
export type SetFlightDivertApiArg = {
  packageId: string;
  flightId: string;
  flightDivertJs: FlightDivert;
};
export type SetFlightTotOffsetApiResponse =
  /** status 200 Successful Response */ PackageDetail;
export type SetFlightTotOffsetApiArg = {
  packageId: string;
  flightId: string;
  flightTotOffsetJs: FlightTotOffset;
};
export type SetFlightCustomNameApiResponse =
  /** status 200 Successful Response */ PackageDetail;
export type SetFlightCustomNameApiArg = {
  packageId: string;
  flightId: string;
  flightCustomNameJs: FlightCustomName;
};
export type SetFlightCallsignApiResponse =
  /** status 200 Successful Response */ PackageDetail;
export type SetFlightCallsignApiArg = {
  packageId: string;
  flightId: string;
  flightCallsignJs: FlightCallsign;
};
export type ResetFlightCallsignApiResponse =
  /** status 200 Successful Response */ PackageDetail;
export type ResetFlightCallsignApiArg = {
  packageId: string;
  flightId: string;
};
export type SetFlightPilotApiResponse =
  /** status 200 Successful Response */ PackageDetail;
export type SetFlightPilotApiArg = {
  packageId: string;
  flightId: string;
  slot: number;
  flightPilotChoiceJs: FlightPilotChoice;
};
export type SetFlightSlotPlayerApiResponse =
  /** status 200 Successful Response */ PackageDetail;
export type SetFlightSlotPlayerApiArg = {
  packageId: string;
  flightId: string;
  slot: number;
  flightSlotPlayerJs: FlightSlotPlayer;
};
export type GetFlightRadiosApiResponse =
  /** status 200 Successful Response */ FlightRadios;
export type GetFlightRadiosApiArg = {
  packageId: string;
  flightId: string;
};
export type SetFlightFrequencyApiResponse =
  /** status 200 Successful Response */ FlightRadios;
export type SetFlightFrequencyApiArg = {
  packageId: string;
  flightId: string;
  flightFrequencyJs: FlightFrequency;
};
export type SetPackageFrequencyApiResponse =
  /** status 200 Successful Response */ FlightRadios;
export type SetPackageFrequencyApiArg = {
  packageId: string;
  flightId: string;
  packageFrequencyJs: PackageFrequency;
};
export type SetFlightTacanApiResponse =
  /** status 200 Successful Response */ FlightRadios;
export type SetFlightTacanApiArg = {
  packageId: string;
  flightId: string;
  flightTacanJs: FlightTacan;
};
export type SetFlightDatalinkApiResponse =
  /** status 200 Successful Response */ FlightRadios;
export type SetFlightDatalinkApiArg = {
  packageId: string;
  flightId: string;
  memberIndex: number;
  datalinkValueJs: DatalinkValue;
};
export type SaveFlightCartridgeApiResponse =
  /** status 200 Successful Response */ FileActionResult;
export type SaveFlightCartridgeApiArg = {
  packageId: string;
  flightId: string;
};
export type GetInstallPreferencesApiResponse =
  /** status 200 Successful Response */ InstallPreferencesState;
export type GetInstallPreferencesApiArg = void;
export type SetInstallPreferencesApiResponse =
  /** status 200 Successful Response */ InstallPreferencesState;
export type SetInstallPreferencesApiArg = {
  installPreferencesUpdateJs: InstallPreferencesUpdate;
};
export type GetPlayerModulesApiResponse =
  /** status 200 Successful Response */ PlayerModule[];
export type GetPlayerModulesApiArg = void;
export type SetPlayerModulesApiResponse =
  /** status 200 Successful Response */ PlayerModule[];
export type SetPlayerModulesApiArg = {
  ownedModulesJs: OwnedModules;
};
export type GetProductionApiResponse =
  /** status 200 Successful Response */ Production | null;
export type GetProductionApiArg = void;
export type RunProductionActionApiResponse =
  /** status 200 Successful Response */ Production;
export type RunProductionActionApiArg = {
  itemId: string;
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
export type ListSavesApiResponse = /** status 200 Successful Response */ Saves;
export type ListSavesApiArg = void;
export type LoadSaveApiResponse =
  /** status 200 Successful Response */ FileActionResult;
export type LoadSaveApiArg = {
  saveId: string;
};
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
export type GetTgoSheetApiResponse =
  /** status 200 Successful Response */ TgoSheet;
export type GetTgoSheetApiArg = {
  tgoId: string;
};
export type RepairTgoUnitApiResponse =
  /** status 200 Successful Response */ TgoSheet;
export type RepairTgoUnitApiArg = {
  tgoId: string;
  unitId: number;
};
export type SetTgoHeadingApiResponse =
  /** status 200 Successful Response */ TgoSheet;
export type SetTgoHeadingApiArg = {
  tgoId: string;
  tgoHeadingChangeJs: TgoHeadingChange;
};
export type SetTgoHiddenOnMfdApiResponse =
  /** status 200 Successful Response */ TgoSheet;
export type SetTgoHiddenOnMfdApiArg = {
  tgoId: string;
  tgoHiddenChangeJs: TgoHiddenChange;
};
export type DisbandTgoGroupApiResponse =
  /** status 200 Successful Response */ TgoSheet;
export type DisbandTgoGroupApiArg = {
  tgoId: string;
};
export type GetTgoPurchaseOptionsApiResponse =
  /** status 200 Successful Response */ TgoPurchaseOptions;
export type GetTgoPurchaseOptionsApiArg = {
  tgoId: string;
};
export type QuoteTgoPurchaseApiResponse =
  /** status 200 Successful Response */ PurchaseQuote;
export type QuoteTgoPurchaseApiArg = {
  tgoId: string;
  tgoPurchaseJs: TgoPurchase;
};
export type BuyTgoGroupApiResponse =
  /** status 200 Successful Response */ TgoSheet;
export type BuyTgoGroupApiArg = {
  tgoId: string;
  tgoPurchaseJs: TgoPurchase;
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
export type GetUnitInfoApiResponse =
  /** status 200 Successful Response */ UnitInfo;
export type GetUnitInfoApiArg = {
  kind: "aircraft" | "ground" | "ship";
  name: string;
};
export type GetUnitBannerApiResponse =
  /** status 200 Successful Response */ Blob;
export type GetUnitBannerApiArg = {
  kind: "aircraft" | "ground" | "ship";
  name: string;
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
export type GetObjectivesApiResponse =
  /** status 200 Successful Response */ CampaignObjectives | null;
export type GetObjectivesApiArg = void;
export type GetWarDiaryApiResponse =
  /** status 200 Successful Response */ WarDiary | null;
export type GetWarDiaryApiArg = void;
export type ExportWarDiaryApiResponse =
  /** status 200 Successful Response */ FileActionResult;
export type ExportWarDiaryApiArg = void;
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
export type CreateTransferApiResponse =
  /** status 200 Successful Response */ TransferJs;
export type CreateTransferApiArg = {
  newTransferJs: NewTransfer;
};
export type CancelTransferApiResponse =
  /** status 204 Successful Response */ void;
export type CancelTransferApiArg = {
  transferId: string;
};
export type SquadronRepair = {
  repair_id: string;
  cost: number;
  affordable: boolean;
};
export type AllowedTask = {
  task: string;
  auto_assign: boolean;
};
export type SquadronOrderRow = {
  squadron_id: string;
  squadron: string;
  aircraft: string;
  aircraft_id: string;
  unit_cost: number;
  owned: number;
  max_aircraft?: number;
  pending: number;
  max_add: number;
  max_remove: number;
};
export type AirWingPilot = {
  id: string;
  name: string;
  player: boolean;
  alive: boolean;
  status: string;
  status_text: string;
  return_turn?: number;
  note: string;
  skill: string;
  sorties: number;
  kills: number;
  player_refusal?: string;
  leave_refusal?: string;
  on_leave: boolean;
};
export type AirWingSquadron = {
  id: string;
  name: string;
  nickname?: string;
  aircraft: string;
  sidc: string;
  base_id: string;
  base: string;
  destination?: string;
  owned: number;
  max_aircraft?: number;
  initial: number;
  purchased: number;
  destroyed: number;
  available: number;
  untasked_crewed: number;
  in_maintenance: number;
  maintenance_text: string;
  repair?: SquadronRepair;
  pilots_ready: number;
  pilots_alive: number;
  sorties: number;
  kills: number;
  next_turn: string[];
  primary_task: string;
  tasks: AllowedTask[];
  order?: SquadronOrderRow;
  parking_room: number;
  new_pilot_refusal?: string;
  pilots: AirWingPilot[];
};
export type AirWingBase = {
  id: string;
  name: string;
  squadrons: AirWingSquadron[];
};
export type InventoryRow = {
  key: string;
  base: string;
  aircraft: string;
  task: string;
  target: string;
  pilot: string;
  crew: string;
  allocated: boolean;
};
export type AirWing = {
  blue: boolean;
  squadron_count: number;
  aircraft_count: number;
  pilot_count: number;
  bases: AirWingBase[];
  inventory: InventoryRow[];
  adjustments_enabled: boolean;
};
export type ValidationError = {
  loc: (string | number)[];
  msg: string;
  type: string;
};
export type HttpValidationError = {
  detail?: ValidationError[];
};
export type CommandError = {
  detail: string;
};
export type PrimaryTask = {
  task: string;
};
export type AutoAssign = {
  task: string;
  enabled: boolean;
};
export type LiveryChoice = {
  label: string;
  livery_id?: string;
  use_livery_set: boolean;
  selected: boolean;
};
export type SetLivery = {
  livery_id?: string | null;
  use_livery_set?: boolean;
};
export type SquadronTransferDestination = {
  id: string;
  name: string;
  room: number;
  refusal?: string;
  overflow: string[];
  selected: boolean;
};
export type SquadronTransferOptions = {
  room_here: number;
  destinations: SquadronTransferDestination[];
};
export type SetDestination = {
  destination_id?: string | null;
};
export type NewPilot = {
  name: string;
};
export type PilotUpdate = {
  player?: boolean | null;
  on_leave?: boolean | null;
  name?: string | null;
};
export type AirWingConfigBase = {
  id: string;
  name: string;
};
export type AirWingConfigParking = {
  required: number;
  total: number;
  fitting?: number;
};
export type AirWingConfigSquadron = {
  id: string;
  name: string;
  nickname?: string;
  aircraft: string;
  aircraft_id: string;
  primary_task: string;
  primary_tasks: string[];
  tasks: AllowedTask[];
  max_size: number;
  base_id: string;
  bases: AirWingConfigBase[];
  parking: AirWingConfigParking;
  player_names: string[];
  player_names_refusal?: string;
  presets: string[];
};
export type AirWingConfigAircraftOption = {
  aircraft_id: string;
  aircraft: string;
  player_module: boolean;
  squadron_count: number;
  primary_tasks: string[];
  bases: AirWingConfigBase[];
  presets: string[];
};
export type AirWingConfigSide = {
  side: string;
  faction: string;
  squadrons: AirWingConfigSquadron[];
  aircraft_options: AirWingConfigAircraftOption[];
};
export type AirWingConfig = {
  replans: boolean;
  sides: AirWingConfigSide[];
};
export type ConfigTarget = "draft" | "campaign";
export type SquadronConfigUpdate = {
  name?: string | null;
  nickname?: string | null;
  max_size?: number | null;
  primary_task?: string | null;
  base_id?: string | null;
  player_names?: string[] | null;
};
export type AirWingConfigReplacePreset = {
  preset: string;
};
export type ConfigSide = "blue" | "red";
export type AirWingConfigNewSquadron = {
  aircraft_id: string;
  base_id: string;
  primary_task: string;
  preset?: string | null;
};
export type AirWingConfigRemoveAircraft = {
  aircraft_id: string;
};
export type AirWingFileResult = {
  path?: string;
};
export type FactionUnitGroup = {
  key: string;
  label: string;
  units: string[];
  addable: string[];
  player_modules: string[];
};
export type FactionSheet = {
  name: string;
  description: string;
  authors: string;
  requirements: {
    [key: string]: string;
  };
  has_jtac: boolean;
  doctrine: string;
  doctrines: string[];
  groups: FactionUnitGroup[];
};
export type AirWingConfigFactionUnit = {
  group: string;
  unit: string;
};
export type AirWingConfigFactionJtac = {
  has_jtac: boolean;
};
export type AirWingConfigFactionDoctrine = {
  doctrine: string;
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
export type GroundUnitRow = {
  unit_id: string;
  name: string;
  unit_cost: number;
  owned: number;
  pending: number;
  max_add: number;
};
export type FrontLineStance = {
  enemy_id: string;
  enemy: string;
  stance: string;
};
export type GroundForces = {
  units: GroundUnitRow[];
  recruitment_refusal?: string;
  has_factory: boolean;
  present: number;
  ordered: number;
  transferring: number;
  deployable_limit?: number;
  reserve?: number;
  front_lines: FrontLineStance[];
  stance_options: string[];
  front_line_cheats: boolean;
};
export type GroundOrderLine = {
  unit_id: string;
  quantity: number;
};
export type GroundOrders = {
  orders: GroundOrderLine[];
};
export type Stance = {
  stance: string;
};
export type DepartingConvoy = {
  name: string;
  kind: "convoy" | "cargo-ship";
  destination_id: string;
  destination: string;
  size: number;
  units: UnitCountJs[];
};
export type PlannedPackage = {
  id: string;
};
export type TransferDestination = {
  id: string;
  name: string;
};
export type TransferableUnit = {
  unit_id: string;
  name: string;
  available: number;
};
export type TransportSquadron = {
  id: string;
  label: string;
  capacity: number;
};
export type TransferOptions = {
  destinations: TransferDestination[];
  destination_id?: string;
  units: TransferableUnit[];
  squadrons: TransportSquadron[];
  no_squadron_warning?: string;
};
export type BaseRadios = {
  has_frequency: boolean;
  has_tacan: boolean;
  has_icls: boolean;
  has_link4: boolean;
  frequency_mhz?: number;
  tacan_channel?: number;
  tacan_band?: string;
  tacan_callsign?: string;
  icls_channel?: number;
  icls_callsign?: string;
  link4_mhz?: number;
  warnings: string[];
};
export type BaseActions = {
  can_transfer: boolean;
  can_plan_transport: boolean;
  can_attack_airfield: boolean;
  cheat_capture?: string;
  cheat_runway?: string;
  radios?: BaseRadios;
};
export type BaseRadiosUpdate = {
  frequency_mhz?: number | null;
  tacan_channel?: number | null;
  tacan_band?: string | null;
  tacan_callsign?: string | null;
  icls_channel?: number | null;
  icls_callsign?: string | null;
  link4_mhz?: number | null;
};
export type FrontLineCheat = {
  advance: boolean;
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
export type FlightRouteWaypoint = {
  index: number;
  name: string;
  type: string;
  position: LatLng;
  altitude_ft: number;
  altitude_reference: string;
  time?: string;
  time_kind?: string;
  is_tot: boolean;
  min_fuel_lb?: number;
  is_movable: boolean;
  include_in_path: boolean;
  can_delete: boolean;
  delete_degrades: boolean;
  can_insert_after: boolean;
  threat?: string;
};
export type FlightRoute = {
  flight_id: string;
  blue: boolean;
  recreate_tasks: string[];
  is_custom: boolean;
  bulk_altitude_ft: number;
  min_altitude_ft: number;
  max_altitude_ft: number;
  waypoints: FlightRouteWaypoint[];
};
export type WaypointAltitude = {
  altitude_ft: number;
};
export type WaypointName = {
  name: string;
};
export type PredefinedWaypoint = {
  name: string;
  description: string;
  has_siblings: boolean;
};
export type NewPredefinedWaypoint = {
  name: string;
  same_location?: boolean;
};
export type RecreateRoute = {
  task: string;
};
export type PayloadWeapon = {
  clsid: string;
  name: string;
};
export type PayloadPylonOptions = {
  number: number;
  weapons: PayloadWeapon[];
};
export type PayloadOption = {
  id: boolean | number | number | string | null;
  label: string;
};
export type PayloadProperty = {
  id: string;
  label: string;
  control: string;
  section?: string;
  minimum?: number;
  maximum?: number;
  options: PayloadOption[];
};
export type WeaponSetting = {
  id: string;
  label: string;
  control: string;
  value: boolean | number | number | string | null;
  read_only: boolean;
  minimum?: number;
  maximum?: number;
  unit?: string;
  options: PayloadOption[];
};
export type MemberPylon = {
  number: number;
  weapon?: PayloadWeapon;
  replaced_weapon?: string;
  settings: WeaponSetting[];
};
export type WeaponLaserCode = {
  code?: number;
  label: string;
};
export type MemberPayload = {
  index: number;
  pilot?: string;
  is_player: boolean;
  loadout: string;
  custom: boolean;
  pylons: MemberPylon[];
  tgp_laser_code?: number;
  weapon_laser_code?: number;
  weapon_laser_codes: WeaponLaserCode[];
  liveries: LiveryChoice[];
  properties: {
    [key: string]: boolean | number | number | string | null;
  };
};
export type FlightPayload = {
  aircraft: string;
  fuel: number;
  fuel_max: number;
  same_loadout: boolean;
  same_livery: boolean;
  restrict_weapons_by_date: boolean;
  date: string;
  loadouts: string[];
  pylons: PayloadPylonOptions[];
  properties: PayloadProperty[];
  members: MemberPayload[];
};
export type FlightFuel = {
  fuel: number;
};
export type SameForAll = {
  same: boolean;
};
export type PayloadFile = {
  path?: string;
};
export type MemberLoadoutName = {
  name: string;
};
export type MemberCustomLoadout = {
  custom: boolean;
};
export type MemberPylonWeapon = {
  clsid?: string | null;
};
export type PayloadValue = {
  id: string;
  value?: boolean | number | number | string | null;
};
export type TgpLaserCode = {
  assigned: boolean;
};
export type WeaponLaserCodeChoice = {
  code?: number | null;
};
export type MemberLivery = {
  livery_id?: string | null;
  use_livery_set?: boolean;
};
export type SavePayload = {
  name: string;
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
export type CampaignStateJs = "continue" | "win" | "loss";
export type ObjectiveTarget = {
  id: string;
  name: string;
  position: LatLng;
  remaining: boolean;
};
export type CampaignObjective = {
  title: string;
  kind: string;
  target: string;
  state: string;
  deadline?: number;
  turns_left?: number;
  done?: number;
  total?: number;
  reward: string;
  expected: string;
  granted: string;
  resolved_turn?: number;
  targets: ObjectiveTarget[];
};
export type ObjectivesSummary = {
  met: number;
  missed: number;
  total: number;
  in_progress: CampaignObjective[];
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
  campaign_state: CampaignStateJs;
  warnings: string[];
  objectives?: ObjectivesSummary;
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
export type SortieAward = {
  kind: string;
  name: string;
  abbreviation: string;
  reason: string;
};
export type SortieCard = {
  pilot_id: string;
  pilot: string;
  squadron: string;
  aircraft: string;
  flight: string;
  task: string;
  target: string;
  package_result: string;
  package_tone: ToneJs;
  air_kills: number;
  ground_kills: number;
  naval_kills: number;
  fate: string;
  fate_tone: ToneJs;
  flight_time: string;
  sorties_logged?: number;
  rescues?: number;
  awards?: SortieAward[];
};
export type ObjectiveLine = {
  title: string;
  met: boolean;
  granted: string;
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
  your_sorties: SortieCard[];
  applied: boolean;
  pilots_captured?: PilotLine[];
  pilots_still_down?: number;
  budget_next_turn?: number;
  income_next_turn?: number;
  objectives?: ObjectiveLine[];
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
export type NewGameCampaign = {
  id: string;
  name: string;
  theater: string;
  authors: string;
  description: string;
  version: string;
  compatible: boolean;
  warning?: string;
  era?: string;
  start_date?: string;
  performance: number;
  performance_label: string;
  performance_text: string;
  recommended_blue_faction: string;
  recommended_red_faction: string;
};
export type NewGameTimePeriod = {
  name: string;
  start_date: string;
};
export type NewGameModChoice = {
  key: string;
  label: string;
};
export type NewGameOptions = {
  campaigns: NewGameCampaign[];
  factions: string[];
  time_periods: NewGameTimePeriod[];
  default_time_period: string;
  mods: NewGameModChoice[];
};
export type CampaignPreviewBase = {
  name: string;
  position: LatLng;
  side: string;
  kind: string;
};
export type CampaignPreviewLink = {
  from_index: number;
  to_index: number;
  front_line: boolean;
};
export type CampaignPreview = {
  south_west?: LatLng;
  north_east?: LatLng;
  bases: CampaignPreviewBase[];
  links: CampaignPreviewLink[];
  blue_bases: number;
  red_bases: number;
  front_lines: number;
};
export type CampaignDefaults = {
  settings_pages: SettingsPage[];
  blue_faction: string;
  red_faction: string;
  start_date?: string;
  time_period?: string;
  player_budget: number;
  enemy_budget: number;
  advanced_iads_available: boolean;
  no_carrier: boolean;
  no_lha: boolean;
  no_player_navy: boolean;
  no_enemy_navy: boolean;
  squadrons_start_full: boolean;
  mods: string[];
};
export type NewGameFactionChoice = {
  name: string;
  removed?: {
    [key: string]: string[];
  };
  added?: {
    [key: string]: string[];
  };
  has_jtac?: boolean | null;
  doctrine?: string | null;
};
export type SaveFaction = {
  faction: NewGameFactionChoice;
  name: string;
  description?: string;
  authors?: string;
};
export type NewGameGeneration = {
  status: string;
  step?: string;
  step_index: number;
  step_count: number;
  error?: string;
};
export type NewGameRequest = {
  campaign_id: string;
  blue: NewGameFactionChoice;
  red: NewGameFactionChoice;
  start_date: string;
  player_budget: number;
  enemy_budget: number;
  inverted?: boolean;
  advanced_iads?: boolean;
  no_carrier?: boolean;
  no_lha?: boolean;
  no_player_navy?: boolean;
  no_enemy_navy?: boolean;
  squadrons_start_full?: boolean;
  mods?: string[];
  settings?: {
    [key: string]: boolean | number | number | string;
  };
  seed?: number | null;
};
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
  objectives: string[];
};
export type PackageEditorFlight = {
  id: string;
  task: string;
  aircraft: string;
  count: number;
  clients: number;
  missing_pilots: number;
  squadron: string;
  departure: string;
  custom_name?: string;
  start_type: string;
  startup: string;
  takeoff: string;
  cancelable: boolean;
};
export type PackageDetail = {
  id: string;
  blue: boolean;
  task?: string;
  description: string;
  custom_name?: string;
  target: string;
  tot?: string;
  auto_asap: boolean;
  tot_locked: boolean;
  can_auto_create: boolean;
  closest_base?: string;
  closest_base_distance_nm?: number;
  transport_origin_id?: string;
  objectives: string[];
  flights: PackageEditorFlight[];
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
export type PackageName = {
  name: string;
};
export type PackageTot = {
  tot: string;
};
export type FlightSquadronOption = {
  id: string;
  name: string;
  base: string;
  available: number;
  max_size: number;
  required_start_type?: string;
};
export type FlightAircraftOption = {
  id: string;
  name: string;
  player_module: boolean;
  squadrons: FlightSquadronOption[];
};
export type FlightTaskOption = {
  task: string;
  aircraft: FlightAircraftOption[];
};
export type FlightOptions = {
  tasks: FlightTaskOption[];
  start_types: string[];
};
export type StartType = "Cold" | "Warm" | "Runway" | "In Flight";
export type NewFlight = {
  task: string;
  squadron_id: string;
  size: number;
  start_type?: StartType | null;
};
export type AutoCreateAircraft = {
  id: string;
  name: string;
};
export type AutoCreateTask = {
  task: string;
  default_count: number;
  aircraft: AutoCreateAircraft[];
};
export type AutoCreateOptions = {
  primary: AutoCreateTask[];
  support: AutoCreateTask[];
  excluded_with_cas: string[];
  min_count: number;
  max_count: number;
};
export type AutoCreateFlight = {
  task: string;
  count: number;
  aircraft?: string | null;
};
export type AutoCreateRequest = {
  flights: AutoCreateFlight[];
};
export type FlightSettingsSquadron = {
  id: string;
  name: string;
  aircraft: string;
  base: string;
  available: number;
};
export type FlightDivertOption = {
  id: string;
  name: string;
};
export type FlightCallsign = {
  name: string;
  number: number;
};
export type FlightPilotOption = {
  id: string;
  name: string;
  player: boolean;
};
export type FlightPilotSlot = {
  pilot?: FlightPilotOption;
  player_refusal?: string;
};
export type FlightSettings = {
  id: string;
  task: string;
  aircraft: string;
  departure: string;
  arrival: string;
  startup: string;
  editable: boolean;
  squadron: FlightSettingsSquadron;
  squadron_options: FlightSettingsSquadron[];
  count: number;
  max_count: number;
  start_type: string;
  start_types: string[];
  start_type_locked: boolean;
  divert_id?: string;
  divert_options: FlightDivertOption[];
  tot_offset_seconds: number;
  custom_name?: string;
  callsign?: FlightCallsign;
  callsign_names: string[];
  callsign_min_number: number;
  callsign_max_number: number;
  slots: FlightPilotSlot[];
  free_pilots: FlightPilotOption[];
};
export type FlightSquadronChanged = {
  flight_id: string;
  package: PackageDetail;
};
export type FlightSquadronChoice = {
  squadron_id: string;
};
export type FlightSize = {
  size: number;
};
export type FlightStartType = {
  start_type: StartType;
};
export type FlightDivert = {
  divert_id?: string | null;
};
export type FlightTotOffset = {
  seconds: number;
};
export type FlightCustomName = {
  name: string;
};
export type FlightPilotChoice = {
  pilot_id?: string | null;
};
export type FlightSlotPlayer = {
  player: boolean;
};
export type RadioRange = {
  min_mhz: number;
  max_mhz: number;
  step_mhz: number;
  modulation: string;
};
export type DatalinkField = {
  identifier: string;
  label: string;
  max_length: number;
};
export type DatalinkMember = {
  index: number;
  pilot?: string;
  values: {
    [key: string]: string;
  };
};
export type FlightDatalink = {
  name: string;
  fields: DatalinkField[];
  members: DatalinkMember[];
};
export type FlightRadios = {
  frequency_mhz?: number;
  modulation?: string;
  ranges: RadioRange[];
  warnings: string[];
  package_frequency_mhz?: number;
  package_min_mhz: number;
  package_max_mhz: number;
  package_warnings: string[];
  has_tacan: boolean;
  tacan_channel?: number;
  tacan_band?: string;
  tacan_callsign?: string;
  tacan_warnings: string[];
  datalink?: FlightDatalink;
  departure_id: string;
  departure: string;
  cartridge_file?: string;
};
export type FlightFrequency = {
  mhz?: number | null;
  modulation?: string | null;
};
export type PackageFrequency = {
  mhz?: number | null;
};
export type FlightTacan = {
  channel?: number | null;
  band?: string | null;
  callsign?: string | null;
};
export type DatalinkValue = {
  identifier: string;
  value: string;
};
export type InstallPreferences = {
  saved_game_dir: string;
  dcs_install_dir: string;
  prefer_liberation_payloads: boolean;
  setup_preferences_on_every_start: boolean;
  server_port: number;
  autosave_turns: number;
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
  autosave_turns: number;
  allow_empty_install_dir?: boolean;
};
export type PlayerModule = {
  id: string;
  name: string;
  owned: boolean;
};
export type OwnedModules = {
  owned: string[];
};
export type ProductionAction = {
  label: string;
  cost: number;
  affordable: boolean;
};
export type ProductionItem = {
  id: string;
  group:
    | "aircraft-orders"
    | "ground-orders"
    | "maintenance"
    | "repairs"
    | "transfers"
    | "damage"
    | "ships";
  label: string;
  detail: string;
  turns?: number;
  base_id?: string;
  tgo_id?: string;
  action?: ProductionAction;
};
export type Production = {
  in_progress: ProductionItem[];
  to_handle: ProductionItem[];
  next_end_turns?: number;
  budget: number;
};
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
  from_objectives: number;
  total: number;
  bases: BaseIncomeJs[];
  buildings: BuildingIncomeJs[];
};
export type FinancesJs = {
  friendly: CoalitionFinancesJs;
  enemy: CoalitionFinancesJs;
};
export type SaveKind = "turn" | "takeoff" | "manual";
export type Save = {
  id: string;
  kind: SaveKind;
  turn: number;
  game_date: string;
  saved_at: string;
  file_name: string;
};
export type Saves = {
  saves: Save[];
  previous_turn_id?: string;
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
export type TgoUnit = {
  id: number;
  name: string;
  info_kind?: "ground" | "ship";
  info_name?: string;
  state: "operational" | "inoperative" | "repairing" | "destroyed";
  turns_remaining: number;
  repair_cost?: number;
  repair_turns: number;
  repair_affordable: boolean;
};
export type TgoIncome = {
  per_building: number;
  available: number;
  receiving: number;
};
export type TgoHeading = {
  degrees: number;
  can_adjust: boolean;
  to_conflict: number;
};
export type TgoSheet = {
  summary: TgoSummary;
  budget: number;
  is_building_site: boolean;
  units: TgoUnit[];
  income?: TgoIncome;
  heading?: TgoHeading;
  hidden_on_mfd?: boolean;
  can_buy: boolean;
  disband_value: number;
};
export type TgoHeadingChange = {
  degrees: number;
};
export type TgoHiddenChange = {
  hidden: boolean;
};
export type SlotOption = {
  id: string;
  name: string;
  price: number;
};
export type LayoutSlot = {
  id: number;
  group_name: string;
  options: SlotOption[];
  amount: number;
  max_amount: number;
  optional: boolean;
};
export type PurchaseLayout = {
  name: string;
  slots: LayoutSlot[];
};
export type PurchaseForceGroup = {
  name: string;
  layouts: PurchaseLayout[];
};
export type TgoPurchaseOptions = {
  force_groups: PurchaseForceGroup[];
};
export type PurchaseQuote = {
  price: number;
  credit: number;
  cost: number;
  affordable: boolean;
};
export type SlotChoice = {
  slot: number;
  unit_type: string;
  amount: number;
};
export type TgoPurchase = {
  force_group: string;
  layout: string;
  choices: SlotChoice[];
};
export type UnitInfo = {
  kind: "aircraft" | "ground" | "ship";
  name: string;
  display_name: string;
  manufacturer: string;
  country_of_origin: string;
  role: string;
  year_introduced: string;
  tasks: string[];
  description: string;
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
  pilot_id: string;
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
export type CampaignObjectives = {
  turn: number;
  objectives: CampaignObjective[];
};
export type WarDiaryBase = {
  id: string;
  name: string;
  taken: boolean;
};
export type WarDiaryFront = {
  name: string;
  moved_km: number;
};
export type WarDiaryPackage = {
  task: string;
  target: string;
  flights: string[];
  lost: number;
  aircraft: number;
  result: string;
  tone: ToneJs;
};
export type WarDiaryLoss = {
  name: string;
  count: number;
};
export type WarDiaryPilot = {
  pilot_id?: string;
  name: string;
  squadron: string;
  aircraft: string;
  fate: string;
};
export type WarDiaryAward = {
  pilot_id: string;
  pilot: string;
  kind: string;
  name: string;
  abbreviation: string;
  reason: string;
};
export type WarDiaryEntry = {
  turn: number;
  date: string;
  weather: string;
  verdict: string;
  verdict_tone: ToneJs;
  summary: string;
  air_kills_friendly: number;
  air_kills_enemy: number;
  ground_kills_friendly: number;
  ground_kills_enemy: number;
  bases: WarDiaryBase[];
  fronts: WarDiaryFront[];
  packages: WarDiaryPackage[];
  friendly_losses: WarDiaryLoss[];
  enemy_losses: WarDiaryLoss[];
  pilots: WarDiaryPilot[];
  awards: WarDiaryAward[];
  budget_next_turn?: number;
  income_next_turn?: number;
};
export type WarDiary = {
  campaign: string;
  since_turn?: number;
  entries: WarDiaryEntry[];
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
export type NewTransferLine = {
  unit_id: string;
  count: number;
};
export type NewTransfer = {
  origin_id: string;
  destination_id: string;
  units: NewTransferLine[];
  airlift?: boolean;
  squadron_id?: string | null;
};
export const {
  useGetAirWingQuery,
  useSetSquadronPrimaryTaskMutation,
  useSetSquadronAutoAssignMutation,
  useGetSquadronLiveriesQuery,
  useSetSquadronLiveryMutation,
  useGetSquadronDestinationsQuery,
  useSetSquadronDestinationMutation,
  useCreatePlayerPilotMutation,
  useUpdatePilotMutation,
  useGetAirWingConfigQuery,
  useUpdateConfigSquadronMutation,
  useRemoveConfigSquadronMutation,
  useSetConfigSquadronAutoAssignMutation,
  useGetConfigSquadronLiveriesQuery,
  useSetConfigSquadronLiveryMutation,
  useRerollConfigSquadronNicknameMutation,
  useReplaceConfigSquadronMutation,
  useAddConfigSquadronMutation,
  useRemoveConfigAircraftSquadronsMutation,
  useSaveAirWingFileMutation,
  useLoadAirWingFileMutation,
  useGetConfigFactionQuery,
  useAddConfigFactionUnitMutation,
  useSetConfigFactionJtacMutation,
  useSetConfigFactionDoctrineMutation,
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
  useGetGroundForcesQuery,
  useOrderGroundUnitsMutation,
  useSetFrontLineStanceMutation,
  useGetDepartingConvoysQuery,
  useAttackDepartingConvoyMutation,
  useGetTransferOptionsQuery,
  useGetBaseActionsQuery,
  useSetBaseRadiosMutation,
  useCheatMoveFrontLineMutation,
  useCheatRunwayStateMutation,
  useCheatCaptureBaseMutation,
  useControlPointDestinationInRangeQuery,
  useSetControlPointDestinationMutation,
  useClearControlPointDestinationMutation,
  useGetDebugHoldZonesQuery,
  useGetDebugJoinZonesQuery,
  useListDownedPilotsQuery,
  useGetDownedPilotByIdQuery,
  useGetFlightRouteQuery,
  useMoveFlightWaypointMutation,
  useSetFlightWaypointAltitudeMutation,
  useRenameFlightWaypointMutation,
  useDeleteFlightWaypointMutation,
  useInsertFlightNavWaypointMutation,
  useAddFlightRtbWaypointMutation,
  useListPredefinedWaypointsQuery,
  useAddPredefinedWaypointMutation,
  useSetFlightRouteAltitudeMutation,
  useRecreateFlightRouteMutation,
  useGetFlightPayloadQuery,
  useSetFlightFuelMutation,
  useSetSameLoadoutMutation,
  useSetSameLiveryMutation,
  useBackupFlightPayloadsMutation,
  useSetMemberLoadoutMutation,
  useSetMemberCustomLoadoutMutation,
  useSetMemberPylonMutation,
  useSetMemberWeaponSettingMutation,
  useResetMemberWeaponSettingsMutation,
  useSetMemberTgpLaserCodeMutation,
  useSetMemberWeaponLaserCodeMutation,
  useSetMemberLiveryMutation,
  useSetMemberPropertyMutation,
  useSaveMemberPayloadMutation,
  useListFlightsQuery,
  useSelectFlightMutation,
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
  useGetNewGameOptionsQuery,
  useGetCampaignPreviewQuery,
  useGetCampaignDefaultsQuery,
  useGetNewGameFactionQuery,
  useSaveNewGameFactionMutation,
  useGetNewGameGenerationQuery,
  useStartNewGameGenerationMutation,
  useCancelNewGameGenerationMutation,
  useBeginNewGameMutation,
  useListPackagesQuery,
  useCreatePackageMutation,
  useDeletePlayerPackagesMutation,
  useGetPackageQuery,
  useDeletePackageMutation,
  useRenamePackageMutation,
  useSetPackageTotMutation,
  useSetPackageTotEarliestMutation,
  useGetFlightOptionsQuery,
  useAddPackageFlightMutation,
  useRemovePackageFlightMutation,
  useGetAutoCreateOptionsQuery,
  useAutoCreatePackageMutation,
  useGetFlightSettingsQuery,
  useSetFlightSquadronMutation,
  useSetFlightSizeMutation,
  useSetFlightStartTypeMutation,
  useSetFlightDivertMutation,
  useSetFlightTotOffsetMutation,
  useSetFlightCustomNameMutation,
  useSetFlightCallsignMutation,
  useResetFlightCallsignMutation,
  useSetFlightPilotMutation,
  useSetFlightSlotPlayerMutation,
  useGetFlightRadiosQuery,
  useSetFlightFrequencyMutation,
  useSetPackageFrequencyMutation,
  useSetFlightTacanMutation,
  useSetFlightDatalinkMutation,
  useSaveFlightCartridgeMutation,
  useGetInstallPreferencesQuery,
  useSetInstallPreferencesMutation,
  useGetPlayerModulesQuery,
  useSetPlayerModulesMutation,
  useGetProductionQuery,
  useRunProductionActionMutation,
  useGetIntelReportQuery,
  useGetStatsReportQuery,
  useGetFinancesReportQuery,
  useListSavesQuery,
  useLoadSaveMutation,
  useListSupplyRoutesQuery,
  useListTgosQuery,
  useGetTgoByIdQuery,
  useGetTgoSummaryQuery,
  useGetTgoSheetQuery,
  useRepairTgoUnitMutation,
  useSetTgoHeadingMutation,
  useSetTgoHiddenOnMfdMutation,
  useDisbandTgoGroupMutation,
  useGetTgoPurchaseOptionsQuery,
  useQuoteTgoPurchaseMutation,
  useBuyTgoGroupMutation,
  useTgoDestinationInRangeQuery,
  useSetTgoDestinationMutation,
  useClearTgoDestinationMutation,
  useGetUnitInfoQuery,
  useGetUnitBannerQuery,
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
  useGetObjectivesQuery,
  useGetWarDiaryQuery,
  useExportWarDiaryMutation,
  useImportLayoutsMutation,
  useGeneratePretenseCampaignMutation,
  useListTransfersQuery,
  useCreateTransferMutation,
  useCancelTransferMutation,
} = injectedRtkApi;
