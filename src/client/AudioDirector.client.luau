-- Decides what you hear: title music -> race music, wind that rises with speed, the crackling camp fire,
-- the odd far-off vulture. Hoofbeats and horse noises are played by Mounts.client where the horse is.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local MapData = require(Shared.MapData)
local AudioIds = require(Shared.AudioIds)
local Sfx = require(Shared.Sfx)
local Feel = require(script.Parent.Feel)

Sfx.init()
local have, total = Sfx.status()
print(("[SBR audio] %d/%d sounds have a Roblox asset id%s"):format(have, total, have == 0 and " - see docs/audio.md to upload them" or ""))

-- ---- title ------------------------------------------------------------------------------------
Sfx.setMusic("theme_title", 2.5)
local menace = Sfx.loop("ambience_gogogo", { volume = 1 })
local wind = Sfx.loop("ambience_wind", { volume = 0 })
local windBase = AudioIds.ambience_wind.volume

-- ---- the ride begins --------------------------------------------------------------------------------
Feel.Started.Event:Connect(function()
	Sfx.setMusic(nil, 0.35)
	Sfx.fadeTo(menace, 0, 1.2, true)
	menace = nil
	Sfx.play("stinger_start", { volume = 1 })
	-- let the stinger land, then bring in the race theme
	task.delay(2.8, function()
		Sfx.setMusic("theme_race", 3)
	end)
end)

-- ---- camp fire (3D) -----------------------------------------------------------------------------------
local ambient = Instance.new("Folder")
ambient.Name = "AmbientSounds"
ambient.Parent = workspace
for _, item in MapData.Landmarks do
	if item.name == "camp_fire" then
		local p = Instance.new("Part")
		p.Name = "CampFireSound"
		p.Anchored = true
		p.CanCollide = false
		p.CanQuery = false
		p.CanTouch = false
		p.Transparency = 1
		p.Size = Vector3.one
		p.Position = Vector3.new(item.x, 2, item.z)
		p.Parent = ambient
		Sfx.loop("ambience_fire", { parent = p, minDistance = 8, maxDistance = 100 })
	end
end

-- ---- wind follows speed -----------------------------------------------------------------------------------
local nextVulture = os.clock() + 25
RunService.RenderStepped:Connect(function()
	if wind then
		local target = windBase * (0.45 + 0.9 * Feel.speedRatio) * (Feel.started and 1 or 0.6)
		wind.Volume = wind.Volume + (target - wind.Volume) * 0.08
	end
	local now = os.clock()
	if Feel.started and now > nextVulture then
		nextVulture = now + 40 + math.random() * 50
		local cam = workspace.CurrentCamera
		if cam then
			local a = math.random() * math.pi * 2
			local p = Instance.new("Part")
			p.Anchored = true
			p.CanCollide = false
			p.CanQuery = false
			p.Transparency = 1
			p.Size = Vector3.one
			p.Position = cam.CFrame.Position + Vector3.new(math.cos(a) * 220, 40, math.sin(a) * 220)
			p.Parent = ambient
			Sfx.play("vulture", { parent = p, volume = 0.7, minDistance = 40, maxDistance = 400 })
			task.delay(4, function()
				p:Destroy()
			end)
		end
	end
end)

-- ---- music intensity: swell a touch when galloping ------------------------------------------------------
local baseMusic = Config.Audio.Music
RunService.Heartbeat:Connect(function()
	if Feel.started and Feel.sprinting then
		Sfx.setGroupVolume("Music", math.min(1, baseMusic * 1.1))
	end
end)
