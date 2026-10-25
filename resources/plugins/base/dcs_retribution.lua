-- the state.json file will be updated according to this schedule and on mission end
local WRITESTATE_SCHEDULE_IN_SECONDS = 15

logger = mist.Logger:new("DCSRetribution", "info")
logger:info("Check that json.lua is loaded : json = "..tostring(json))

crash_events = {} -- killed aircraft will be added via S_EVENT_CRASH event
dead_events = {} -- killed units will be added via S_EVENT_DEAD event
unit_lost_events = {} -- killed units will be added via S_EVENT_UNIT_LOST
kill_events = {} -- killed units will be added via S_EVENT_KILL 
kill_attributions = {} -- {initiator = ..., target = ...} pairs from S_EVENT_KILL, to credit pilots
base_capture_events = {}
destroyed_objects_positions = {} -- will be added via S_EVENT_DEAD event
damaged_units_life = {} -- unit/static name -> remaining life ratio, tracked via S_EVENT_HIT
killed_unit_names = {} -- names reported by crash/dead/lost/kill events, excluded from damaged_units
ejection_events = {} -- {unit=<aircraft unit name>, x=, z=} added via S_EVENT_EJECTION
csar_rescued = {} -- UUID strings of downed pilots rescued by Ops.CSAR (see OpsCSAR.lua)
mission_ended = false
dirty_state = false -- Track if state has changed and needs writing

local function ends_with(str, ending)
   return ending == "" or str:sub(-#ending) == ending
end

local function messageAll(message)
    local msg = {}
    msg.text = message
    msg.displayTime = 25
    msg.msgFor = {coa = {'all'}}
    mist.message.add(msg)
end

-- Remaining life ratio (0..1) of a unit or static object, or nil if unknown.
-- Units expose getLife0(); statics only have getLife(), their initial life comes from getDesc().life.
local function get_life_ratio(object)
    local ok, ratio = pcall(function()
        if not object or not object:isExist() then
            return nil
        end
        local life = object:getLife()
        local life0 = nil
        if object.getLife0 then
            life0 = object:getLife0()
        end
        if (not life0 or life0 <= 0) and object.getDesc then
            local desc = object:getDesc()
            if desc and desc.life then
                life0 = desc.life
            end
        end
        if not life or not life0 or life0 <= 0 then
            return nil
        end
        return math.max(0, math.min(1, life / life0))
    end)
    if ok then
        return ratio
    end
    return nil
end

local function find_damageable_object(name)
    local object = Unit.getByName(name)
    if not object then
        object = StaticObject.getByName(name)
    end
    return object
end

-- Refreshes the life ratio of a tracked unit. Units that no longer exist (despawned
-- after landing, for instance) keep their last known ratio. Returns true if it changed.
local function refresh_damaged_unit(name)
    local ratio = get_life_ratio(find_damageable_object(name))
    if ratio and ratio ~= damaged_units_life[name] then
        damaged_units_life[name] = ratio
        return true
    end
    return false
end

local function collect_damaged_units()
    local damaged_units = {}
    for name, _ in pairs(damaged_units_life) do
        if not killed_unit_names[name] then
            refresh_damaged_unit(name)
            local ratio = damaged_units_life[name]
            if ratio and ratio < 1 then
                damaged_units[#damaged_units + 1] = { ["name"] = name, ["life"] = ratio }
            end
        end
    end
    return damaged_units
end

function write_state()
    local _debriefing_file_location = debriefing_file_location
    if not debriefing_file_location or debriefing_file_location == "" then
        error("Unable to save DCS Retribution state: debriefing file path is unavailable")
    end

    if not json then
        error("Unable to save DCS Retribution state, JSON library is not loaded")
    end

    local fp, open_error = io.open(_debriefing_file_location, 'w')
    if not fp then
        error("Unable to open state file for writing: "..tostring(_debriefing_file_location).." ("..tostring(open_error)..")")
    end
    local game_state = {
        ["crash_events"] = crash_events,
        ["dead_events"] = dead_events,
        ["base_capture_events"] = base_capture_events,
		["unit_lost_events"] = unit_lost_events,
		["kill_events"] = kill_events,
		["kill_attributions"] = kill_attributions,
        ["mission_ended"] = mission_ended,
        ["destroyed_objects_positions"] = destroyed_objects_positions,
        ["damaged_units"] = collect_damaged_units(),
        ["ejection_events"] = ejection_events,
        ["csar_rescued"] = csar_rescued,
    }
    local ok, write_error = pcall(function()
        fp:write(json:encode(game_state))
    end)
    fp:close()
    if not ok then
        error(write_error)
    end
end

local function canWrite(name)
    local f = io.open(name, "a")
    if f then
        f:close()
        return true
    end
    return false
end

local function testDebriefingFilePath(folderPath, folderName, useCurrentStamping)
    if folderPath then
        local filePath = nil
        if not ends_with(folderPath, "\\") then
            folderPath = folderPath .. "\\"
        end
        if useCurrentStamping then
            filePath = string.format("%sstate-%s.json",folderPath, tostring(os.time()))
        else 
            filePath = string.format("%sstate.json",folderPath)
        end
        local isOk = canWrite(filePath)
        if isOk then 
            logger:info(string.format("The state.json file will be created in %s : (%s)",folderName, filePath))
            return filePath
        end
    end
    return nil
end

local function discoverDebriefingFilePath()   
    -- establish a search pattern into the following modes
    -- 1. Environment variable RETRIBUTION_EXPORT_DIR, to support dedicated server hosting
    -- 2. Embedded DCS Retribution dcsRetribution.installPath (set by the app to its install path), to support locally hosted single player
    -- 3. System temporary folder, as set in the TEMP environment variable
    -- 4. Working directory.
    
    local useCurrentStamping = nil
    if os then  
        useCurrentStamping = os.getenv("RETRIBUTION_EXPORT_STAMPED_STATE")
    end

    local installPath = nil
    if dcsRetribution then
        installPath = dcsRetribution.installPath
    end
    
    if os then
        local result = nil
        -- try using the RETRIBUTION_EXPORT_DIR environment variable
        result = testDebriefingFilePath(os.getenv("RETRIBUTION_EXPORT_DIR"), "RETRIBUTION_EXPORT_DIR", useCurrentStamping)
        if result then
            return result
        end
        -- no joy ? maybe there is a valid path in the mission ?
        result = testDebriefingFilePath(installPath, "the DCS Retribution install folder", useCurrentStamping)
        if result then
            return result
        end
        -- there's always the possibility of using the system temporary folder
        result = testDebriefingFilePath(os.getenv("TEMP"), "TEMP", useCurrentStamping)
        if result then
            return result
        end
    end

    -- nothing worked, let's try the last resort folder : current directory.
    if lfs then
        return testDebriefingFilePath(lfs.writedir().."Missions\\", "the working directory", useCurrentStamping)
    end
    
    return nil
end

debriefing_file_location = discoverDebriefingFilePath()
local error_message_shown = false

write_state_error_handling = function()
    local _debriefing_file_location = debriefing_file_location
    if not debriefing_file_location then 
        _debriefing_file_location = "[nil]"
        logger:error("Unable to find where to write DCS Retribution state")
    end

    -- Only write if state has changed since last write
    if dirty_state then
        if pcall(write_state) then
            dirty_state = false -- Reset dirty flag after successful write
            error_message_shown = false
        else
            if not error_message_shown then
                messageAll("Unable to write DCS Retribution state to ".._debriefing_file_location..
                        "\nYou can abort the mission in DCS Retribution.\n"..
                        "\n\nPlease fix your setup in DCS Retribution, make sure you are pointing to the right installation directory from the File/Preferences menu. Then after fixing the path restart DCS Retribution, and then restart DCS."..
                        "\n\nYou can also try to fix the issue manually by replacing the file <dcs_installation_directory>/Scripts/MissionScripting.lua by the one provided there : <dcs_retribution_folder>/resources/scripts/MissionScripting.lua. And then restart DCS. (This will also have to be done again after each DCS update)"..
                        "\n\nIt's not worth playing, the state of the mission will not be recorded.")
                error_message_shown = true
            end
        end
    end

    -- Reschedule quickly if mission is over and we still have unsaved changes,
    -- otherwise use the normal cadence.
    local next_schedule_in_seconds = WRITESTATE_SCHEDULE_IN_SECONDS
    if mission_ended and dirty_state then
        next_schedule_in_seconds = 1
    end
    mist.scheduleFunction(write_state_error_handling, {}, timer.getTime() + next_schedule_in_seconds)
end

local function mark_killed(object)
    if object and object.getName then
        local ok, name = pcall(object.getName, object)
        if ok and name then
            killed_unit_names[name] = true
        end
    end
end

-- Damage is read a moment after the hit, once DCS has applied it to the unit's life.
local function refresh_damaged_unit_after_hit(name)
    if refresh_damaged_unit(name) then
        dirty_state = true
    end
    return nil
end

local function track_hit(target)
    local ok, name = pcall(function()
        local category = Object.getCategory(target)
        if category ~= Object.Category.UNIT and category ~= Object.Category.STATIC then
            return nil
        end
        return target:getName()
    end)
    if not ok or not name then
        return
    end
    if damaged_units_life[name] == nil then
        damaged_units_life[name] = 1
    end
    refresh_damaged_unit(name)
    timer.scheduleFunction(refresh_damaged_unit_after_hit, name, timer.getTime() + 1)
    dirty_state = true
end

activeWeapons = {}
local function onEvent(event)
    if event.id == world.event.S_EVENT_HIT and event.target then
        track_hit(event.target)
    end

    if event.id == world.event.S_EVENT_CRASH and event.initiator then
        crash_events[#crash_events + 1] = event.initiator.getName(event.initiator)
        mark_killed(event.initiator)
        dirty_state = true
    end
   
    if event.id == world.event.S_EVENT_UNIT_LOST and event.initiator then
        unit_lost_events[#unit_lost_events + 1] = event.initiator.getName(event.initiator)
        mark_killed(event.initiator)
        dirty_state = true
    end
	
	if event.id == world.event.S_EVENT_KILL and event.target then
        kill_events[#kill_events + 1] = event.target.getName(event.target)
        if event.initiator and event.initiator.getName then
            kill_attributions[#kill_attributions + 1] = {
                ["initiator"] = event.initiator.getName(event.initiator),
                ["target"] = event.target.getName(event.target),
            }
        end
        mark_killed(event.target)
        dirty_state = true
    end

    if event.id == world.event.S_EVENT_DEAD and event.initiator and event.initiator.getName then
        dead_events[#dead_events + 1] = event.initiator.getName(event.initiator)
        mark_killed(event.initiator)
        local position = event.initiator.getPosition(event.initiator)
        local destruction = {}
        destruction.x = position.p.x
        destruction.y = position.p.y
        destruction.z = position.p.z
        destruction.type = event.initiator:getTypeName()
        destruction.orientation = mist.getHeading(event.initiator) * 57.3
        -- Only track actual units/buildings, not debris/crash models
        if destruction.type ~= nil and 
           string.find(destruction.type, "GENERIC_CRASH_MODEL") == nil and
           string.find(destruction.type, "_CRASH") == nil then
            destroyed_objects_positions[#destroyed_objects_positions + 1] = destruction
        end
        dirty_state = true
    end

    -- Ejection: record the aircraft unit name and its position so Retribution can
    -- place a downed pilot for CSAR. The landing-after-ejection event refines the
    -- position to where the pilot's parachute actually touched down.
    if event.id == world.event.S_EVENT_EJECTION and event.initiator and event.initiator.getName then
        local ok, name = pcall(function() return event.initiator:getName() end)
        if ok and name then
            local ejection = { unit = name }
            local posOk, position = pcall(function() return event.initiator:getPosition() end)
            if posOk and position and position.p then
                ejection.x = position.p.x
                ejection.z = position.p.z
            end
            ejection_events[#ejection_events + 1] = ejection
            dirty_state = true
        end
    end

    if event.id == world.event.S_EVENT_LANDING_AFTER_EJECTION and event.initiator then
        local posOk, position = pcall(function() return event.initiator:getPoint() end)
        if posOk and position then
            -- Refine the most recent ejection that has no landing position yet.
            for i = #ejection_events, 1, -1 do
                local ej = ejection_events[i]
                if not ej.landed then
                    ej.x = position.x
                    ej.z = position.z
                    ej.landed = true
                    dirty_state = true
                    break
                end
            end
        end
    end

    if event.id == world.event.S_EVENT_MISSION_END then
        mission_ended = true
        dirty_state = true
        if pcall(write_state) then
            dirty_state = false
        end
    end

end

mist.addEventHandler(onEvent)

dirty_state = true
write_state_error_handling()

-- Escort leash
-- Escorts are kept within their engagement range relative to the escorted group.
-- This is driven by the mission-injected dcsRetribution.Escorts table.

local function escort_leash_get_group(id)
    local group_id = tonumber(id)
    if not group_id or group_id <= 0 then
        return nil
    end
    -- DCS has no Group.getByID; resolve the mission group id to a name via mist.
    local data = mist.DBs.groupsById and mist.DBs.groupsById[group_id]
    return data and Group.getByName(data.groupName) or nil
end

local function escort_leash_set_roe(group, roe)
    if not group then
        return
    end
    local controller = group:getController()
    if controller then
        controller:setOption(AI.Option.Air.id.ROE, roe)
    end
end

local function escort_leash_update()
    -- Keep running even if dcsRetribution data isn't available yet (trigger ordering)
    if not dcsRetribution or type(dcsRetribution.Escorts) ~= "table" then
        return timer.getTime() + 10
    end

    for _, pair in pairs(dcsRetribution.Escorts) do
        local escort_group = escort_leash_get_group(pair.escortGroupId)
        local escorted_group = escort_leash_get_group(pair.escortedGroupId)

        -- If the escorted group no longer exists (dead/despawned), ensure escort isn't stuck.
        if escort_group and not escorted_group then
            escort_leash_set_roe(escort_group, AI.Option.Air.val.ROE.OPEN_FIRE)
        elseif escort_group and escorted_group then
            local escort_unit = escort_group:getUnit(1)
            local escorted_unit = escorted_group:getUnit(1)
            if escort_unit and escorted_unit then
                local escort_pos = escort_unit:getPoint()
                local escorted_pos = escorted_unit:getPoint()
                local dx = escort_pos.x - escorted_pos.x
                local dz = escort_pos.z - escorted_pos.z
                local distance = math.sqrt(dx * dx + dz * dz)

                local max_dist = tonumber(pair.engagementRangeMeters) or 0
                if max_dist > 0 and distance > max_dist then
                    escort_leash_set_roe(escort_group, AI.Option.Air.val.ROE.RETURN_FIRE)
                else
                    escort_leash_set_roe(escort_group, AI.Option.Air.val.ROE.OPEN_FIRE)
                end
            end
        end
    end

    return timer.getTime() + 10
end

timer.scheduleFunction(escort_leash_update, nil, timer.getTime() + 1)
