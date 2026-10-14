local Lighting = game:GetService("Lighting")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Assets = require(Shared.Assets)
local MapData = require(Shared.MapData)
local SpriteFactory = require(Shared.SpriteFactory)

local function setupLighting()
	for _, child in Lighting:GetChildren() do
		if child:IsA("Sky") or child:IsA("Atmosphere") then
			child:Destroy()
		end
	end
	Lighting.ClockTime = 14
	Lighting.Brightness = 2
	Lighting.GlobalShadows = false
	Lighting.Ambient = Color3.fromRGB(205, 190, 170)
	Lighting.OutdoorAmbient = Color3.fromRGB(235, 220, 195)
	Lighting.ColorShift_Top = Color3.fromRGB(255, 240, 215)
	Lighting.EnvironmentDiffuseScale = 0
	Lighting.EnvironmentSpecularScale = 0
	Lighting.FogColor = Color3.fromRGB(226, 190, 140)
	Lighting.FogStart = 1500
	Lighting.FogEnd = 3000
end

local function textured(part: Part, image: string, studsU: number, studsV: number)
	local tex = Instance.new("Texture")
	tex.Texture = image
	tex.Face = Enum.NormalId.Top
	tex.StudsPerTileU = studsU
	tex.StudsPerTileV = studsV
	tex.Parent = part
end

local function flatPart(name: string, size: Vector3, cf: CFrame, parent: Instance): Part
	local part = Instance.new("Part")
	part.Name = name
	part.Size = size
	part.CFrame = cf
	part.Anchored = true
	part.CanCollide = false
	part.CanQuery = false
	part.CastShadow = false
	part.Material = Enum.Material.SmoothPlastic
	part.Color = Color3.new(1, 1, 1)
	part.TopSurface = Enum.SurfaceType.Smooth
	part.Parent = parent
	return part
end

local function buildGround(map: Folder)
	local size = Config.World.Size
	local ground = flatPart("Ground", Vector3.new(size, 1, size), CFrame.new(0, -0.5, 0), map)
	ground.CanCollide = true
	ground.CanQuery = true
	textured(ground, Assets.Ground.Sand.image, Assets.Ground.Sand.studs, Assets.Ground.Sand.studs)
end

local function buildTrail(map: Folder)
	local folder = Instance.new("Folder")
	folder.Name = "Trail"
	folder.Parent = map

	local width = MapData.Trail.Width
	local points = MapData.Trail.Points
	local edge = Assets.TrailEdge
	local dirtDepth = edge.studsV * edge.dirtFraction
	local blank = edge.studsV - dirtDepth

	for i = 1, #points - 1 do
		local a = Vector3.new(points[i].X, 0, points[i].Y)
		local b = Vector3.new(points[i + 1].X, 0, points[i + 1].Y)
		local length = (b - a).Magnitude + width -- overlap so corners have no gaps
		local mid = (a + b) / 2
		local cf = CFrame.lookAt(mid, b)

		-- Dirt core, slightly narrower so the ragged edge strips cover its border.
		local core = flatPart("Core", Vector3.new(width - 4, 0.1, length), cf + Vector3.new(0, 0.05, 0), folder)
		textured(core, Assets.Ground.Trail.image, Assets.Ground.Trail.studs, Assets.Ground.Trail.studs)

		for _, side in { -1, 1 } do
			-- Strip's long axis runs along the trail; its dirt half faces the trail centre.
			local offset = side * (width / 2 - dirtDepth / 2 + blank / 2 - 0.5)
			local rot = side == 1 and math.pi / 2 or -math.pi / 2
			local stripCF = cf * CFrame.new(offset, 0.1, 0) * CFrame.Angles(0, rot, 0)
			local strip = flatPart("Edge", Vector3.new(length, 0.05, edge.studsV), stripCF, folder)
			textured(strip, edge.image, edge.studsU, edge.studsV)
		end
	end
end

local function distanceToTrail(x: number, z: number): number
	local best = math.huge
	local points = MapData.Trail.Points
	local p = Vector2.new(x, z)
	for i = 1, #points - 1 do
		local a, b = points[i], points[i + 1]
		local ab = b - a
		local t = math.clamp((p - a):Dot(ab) / ab:Dot(ab), 0, 1)
		best = math.min(best, (p - (a + ab * t)).Magnitude)
	end
	return best
end

local function buildProps(map: Folder)
	local folder = Instance.new("Folder")
	folder.Name = "Props"
	folder.Parent = map

	local rng = Random.new(MapData.Seed)
	local rules = MapData.Props
	local half = Config.World.PropHalfExtent
	local spawn = Config.World.SpawnPosition
	local clear = MapData.Trail.Width / 2 + rules.TrailClearance

	local totalWeight = 0
	for _, kind in rules.Kinds do
		totalWeight += kind.weight
	end

	local placed: { Vector2 } = {}
	local attempts = 0
	while #placed < rules.Count and attempts < rules.Count * 30 do
		attempts += 1
		local x = rng:NextNumber(-half, half)
		local z = rng:NextNumber(-half, half)
		local pos = Vector2.new(x, z)

		local ok = distanceToTrail(x, z) > clear
			and (pos - Vector2.new(spawn.X, spawn.Z)).Magnitude > rules.SpawnClearance
		if ok then
			for _, other in placed do
				if (other - pos).Magnitude < rules.MinSpacing then
					ok = false
					break
				end
			end
		end

		if ok then
			local roll = rng:NextNumber(0, totalWeight)
			local chosen = rules.Kinds[1]
			for _, kind in rules.Kinds do
				roll -= kind.weight
				if roll <= 0 then
					chosen = kind
					break
				end
			end
			local scale = rng:NextNumber(chosen.scale[1], chosen.scale[2])
			SpriteFactory.create(Assets.Sprites[chosen.name], Vector3.new(x, 0, z), scale, folder)
			table.insert(placed, pos)
		end
	end
end

local function buildLandmarks(map: Folder)
	local folder = Instance.new("Folder")
	folder.Name = "Landmarks"
	folder.Parent = map
	for _, item in MapData.Landmarks do
		SpriteFactory.create(Assets.Sprites[item.name], Vector3.new(item.x, 0, item.z), item.scale, folder)
	end
end

local function buildBorder(map: Folder)
	local folder = Instance.new("Folder")
	folder.Name = "Border"
	folder.Parent = map
	local rng = Random.new(MapData.Seed + 1)
	local b = MapData.Border
	local def = Assets.Sprites[b.name]
	local d = b.distance
	local n = math.floor(d * 2 / b.spacing)
	for i = 0, n do
		local t = -d + i * b.spacing
		-- Sides are placed in z order so nearer cliffs draw in front of farther ones.
		for _, pos in { Vector3.new(t, 0, -d), Vector3.new(-d, 0, t), Vector3.new(d, 0, t), Vector3.new(t, 0, d) } do
			local jitter = Vector3.new(rng:NextNumber(-6, 6), 0, rng:NextNumber(-6, 6))
			SpriteFactory.create(def, pos + jitter, rng:NextNumber(b.scale[1], b.scale[2]), folder)
		end
	end
end

local function buildSpawn(map: Folder)
	local spawn = Instance.new("SpawnLocation")
	spawn.Anchored = true
	spawn.CanCollide = false
	spawn.Transparency = 1
	spawn.Size = Vector3.new(8, 1, 8)
	spawn.Position = Config.World.SpawnPosition
	spawn.Neutral = true
	spawn.Duration = 0
	spawn.Parent = map
end

setupLighting()
local map = Instance.new("Folder")
map.Name = "Map"
map.Parent = workspace
buildGround(map)
buildTrail(map)
buildProps(map)
buildLandmarks(map)
buildBorder(map)
buildSpawn(map)

-- The Humanoid character is just the physics body now: the client draws a horse and rider over it,
-- so the default avatar (and its name/health bar) is hidden.
local function hideAvatar(character: Model)
	local function hide(d: Instance)
		if d:IsA("BasePart") then
			d.Transparency = 1
			d.CastShadow = false
		elseif d:IsA("Decal") or d:IsA("Texture") then
			d.Transparency = 1
		end
	end
	for _, d in character:GetDescendants() do
		hide(d)
	end
	character.DescendantAdded:Connect(hide)
end

local function onCharacter(character: Model)
	local humanoid = character:WaitForChild("Humanoid") :: Humanoid
	humanoid.WalkSpeed = Config.Player.WalkSpeed
	humanoid.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
	humanoid.HealthDisplayType = Enum.HumanoidHealthDisplayType.AlwaysOff
	hideAvatar(character)
end
Players.PlayerAdded:Connect(function(player)
	player.CharacterAdded:Connect(onCharacter)
end)
for _, player in Players:GetPlayers() do
	if player.Character then
		onCharacter(player.Character)
	end
	player.CharacterAdded:Connect(onCharacter)
end
