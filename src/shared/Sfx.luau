-- Sound playback for the whole game. Every sound is looked up by name in AudioIds; if a sound has no
-- Roblox asset id yet (id = 0) every call here quietly does nothing, so the game runs fine before the
-- audio has been uploaded (see tools/upload_audio.py).
local ContentProvider = game:GetService("ContentProvider")
local Debris = game:GetService("Debris")
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
		for _, def in AudioIds do
			if def.id ~= 0 then
				local s = Instance.new("Sound")
				s.SoundId = "rbxassetid://" .. def.id
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
	local def = AudioIds[name]
	return def ~= nil and def.id ~= 0
end

-- (sounds with an id, total sounds)
function Sfx.status(): (number, number)
	local have, total = 0, 0
	for _, def in AudioIds do
		total += 1
		if def.id ~= 0 then
			have += 1
		end
	end
	return have, total
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
	if not def or def.id == 0 then
		return nil
	end
	Sfx.init()
	local s = Instance.new("Sound")
	s.Name = name
	s.SoundId = "rbxassetid://" .. def.id
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
	if not def or def.id == 0 then
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
