-- Sound playback for the whole game. Every sound is looked up by name; if it can't be found every call
-- here quietly does nothing, so the game runs fine before the audio has been uploaded.
--
-- A sound's Roblox asset id comes from, in order:
--   1. AudioIds.luau (filled in by tools/upload_audio.py, or by hand), or
--   2. a Sound object in a folder called "SBRAudio" in ReplicatedStorage. In Studio you can bulk-import
--      assets/audio/*.ogg, select them in Asset Manager and drag them into that folder; Studio makes a
--      Sound named after each file, and that is all this needs (no copying ids around).
local ContentProvider = game:GetService("ContentProvider")
local Debris = game:GetService("Debris")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local SoundService = game:GetService("SoundService")
local TweenService = game:GetService("TweenService")

local AudioIds = require(script.Parent.AudioIds)
local Config = require(script.Parent.Config)

local Sfx = {}

local groups: { [string]: SoundGroup } = {}
local lastVariant: { [string]: number } = {}
local rng = Random.new()
local currentMusic: Sound? = nil
local currentMusicName: string? = nil
local initialised = false

local KIND_GROUP = { music = "Music", sfx = "Sfx", ambience = "Ambience" }

-- ---- finding sound ids -----------------------------------------------------------------------------------
local FOLDER_NAME = "SBRAudio"
local library: { [string]: string } = {} -- normalised name -> SoundId, from the Studio folder
local watching = false

-- "SBR hoof_dirt_1.ogg" / "Hoof Dirt 1" -> "hoof_dirt_1"
local function normalise(name: string): string
	local n = name:lower()
	n = n:gsub("%.%w+$", "")
	n = n:gsub("^sbr[%s_%-]+", "")
	n = n:gsub("[%s%-]+", "_")
	return n
end

local function indexSound(inst: Instance)
	if inst:IsA("Sound") and inst.SoundId ~= "" then
		library[normalise(inst.Name)] = inst.SoundId
	end
end

local function scanFolder(folder: Instance)
	for _, d in folder:GetDescendants() do
		indexSound(d)
	end
	if not watching then
		watching = true
		folder.DescendantAdded:Connect(function(d)
			task.defer(indexSound, d)
		end)
	end
end

local function findFolder(): Instance?
	return ReplicatedStorage:FindFirstChild(FOLDER_NAME) or SoundService:FindFirstChild(FOLDER_NAME)
end

do
	local folder = findFolder()
	if folder then
		scanFolder(folder)
	else
		ReplicatedStorage.ChildAdded:Connect(function(child)
			if child.Name == FOLDER_NAME and not watching then
				scanFolder(child)
			end
		end)
	end
end

-- The rbxassetid:// string for a sound, or nil if it hasn't been set up yet.
local function soundIdFor(name: string): string?
	local def = AudioIds[name]
	if def and def.id ~= 0 then
		return "rbxassetid://" .. def.id
	end
	return library[name]
end

function Sfx.init()
	if initialised then
		return
	end
	initialised = true
	local master = Instance.new("SoundGroup")
	master.Name = "SBR"
	master.Parent = SoundService
	for kind, name in KIND_GROUP do
		local g = Instance.new("SoundGroup")
		g.Name = name
		g.Volume = Config.Audio[name] or 1
		g.Parent = master
		groups[kind] = g
	end
	-- Warm the cache so the first hoofbeat doesn't stutter.
	task.spawn(function()
		local list = {}
		for name in AudioIds do
			local id = soundIdFor(name)
			if id then
				local s = Instance.new("Sound")
				s.SoundId = id
				table.insert(list, s)
			end
		end
		if #list > 0 then
			pcall(function()
				ContentProvider:PreloadAsync(list)
			end)
		end
		for _, s in list do
			s:Destroy()
		end
	end)
end

function Sfx.has(name: string): boolean
	return AudioIds[name] ~= nil and soundIdFor(name) ~= nil
end

-- (sounds that can play, total sounds)
function Sfx.status(): (number, number)
	local have, total = 0, 0
	for name in AudioIds do
		total += 1
		if soundIdFor(name) then
			have += 1
		end
	end
	return have, total
end

-- Names of sounds that still have no id (for the start-up report).
function Sfx.missing(): { string }
	local out = {}
	for name in AudioIds do
		if not soundIdFor(name) then
			table.insert(out, name)
		end
	end
	table.sort(out)
	return out
end

function Sfx.setGroupVolume(kind: string, volume: number, fade: number?)
	local g = groups[kind]
	if not g then
		return
	end
	if fade and fade > 0 then
		TweenService:Create(g, TweenInfo.new(fade, Enum.EasingStyle.Quad), { Volume = volume }):Play()
	else
		g.Volume = volume
	end
end

local function make(name: string, opts): Sound?
	local def = AudioIds[name]
	local id = def and soundIdFor(name)
	if not def or not id then
		return nil
	end
	Sfx.init()
	local s = Instance.new("Sound")
	s.Name = name
	s.SoundId = id
	s.Volume = def.volume * (opts.volume or 1)
	local jitter = opts.jitter or 0
	s.PlaybackSpeed = (opts.pitch or 1) * (1 + (jitter > 0 and rng:NextNumber(-jitter, jitter) or 0))
	if opts.loop ~= nil then
		s.Looped = opts.loop
	else
		s.Looped = def.loop
	end
	s.SoundGroup = groups[def.kind]
	s.RollOffMode = Enum.RollOffMode.InverseTapered
	s.RollOffMinDistance = opts.minDistance or 14
	s.RollOffMaxDistance = opts.maxDistance or 160
	return s
end

-- Play a one-shot. opts: parent (Instance, makes it 3D), volume, pitch, jitter (random pitch +-), delay.
function Sfx.play(name: string, opts: { [string]: any }?): Sound?
	opts = opts or {}
	local s = make(name, opts)
	if not s then
		return nil
	end
	s.Parent = opts.parent or SoundService
	local function go()
		if s.Parent then
			s:Play()
		end
	end
	if opts.delay and opts.delay > 0 then
		task.delay(opts.delay, go)
	else
		go()
	end
	local def = AudioIds[name]
	Debris:AddItem(s, def.seconds / math.max(0.25, s.PlaybackSpeed) + (opts.delay or 0) + 1.5)
	return s
end

-- Play one of `prefix_1 .. prefix_count`, never the same twice in a row.
function Sfx.variant(prefix: string, count: number, opts: { [string]: any }?): Sound?
	local i = rng:NextInteger(1, count)
	if count > 1 and i == lastVariant[prefix] then
		i = i % count + 1
	end
	lastVariant[prefix] = i
	return Sfx.play(prefix .. "_" .. i, opts)
end

-- Start a looping sound and keep it; returns nil if the sound has no id yet.
function Sfx.loop(name: string, opts: { [string]: any }?): Sound?
	opts = opts or {}
	local s = make(name, opts)
	if not s then
		return nil
	end
	s.Looped = true
	s.Parent = opts.parent or SoundService
	s:Play()
	return s
end

function Sfx.fadeTo(sound: Sound?, volume: number, time: number, destroyAfter: boolean?)
	if not sound or not sound.Parent then
		return
	end
	local tween = TweenService:Create(sound, TweenInfo.new(time, Enum.EasingStyle.Quad), { Volume = volume })
	tween:Play()
	if destroyAfter then
		tween.Completed:Once(function()
			sound:Destroy()
		end)
	end
end

-- Crossfade to a new music track (nil = fade the music out). Calling it with the track already playing is a no-op.
function Sfx.setMusic(name: string?, fade: number?, volumeScale: number?)
	fade = fade or 1.5
	if name == currentMusicName then
		return
	end
	currentMusicName = name
	if currentMusic then
		Sfx.fadeTo(currentMusic, 0, fade :: number, true)
		currentMusic = nil
	end
	if not name then
		return
	end
	local def = AudioIds[name]
	if not def or not soundIdFor(name) then
		return
	end
	local s = make(name, { volume = 0, loop = true })
	if not s then
		return
	end
	s.Parent = SoundService
	s:Play()
	currentMusic = s
	Sfx.fadeTo(s, def.volume * (volumeScale or 1), fade :: number)
end

return Sfx
