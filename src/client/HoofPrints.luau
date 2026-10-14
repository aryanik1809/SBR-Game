-- Hoofprints stamped into the ground behind every horse, fading out over a few seconds.
-- Each print is a little horseshoe made of three flat bars; a fixed pool is recycled so a long ride
-- never piles up parts.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local TrailMath = require(Shared.TrailMath)

local HoofPrints = {}

local cfg = Config.Prints
local folder = Instance.new("Folder")
folder.Name = "HoofPrints"
folder.Parent = workspace

type Print = { parts: { Part }, born: number, life: number, alpha: number, live: boolean }
local pool: { Print } = {}
local nextIndex = 1 -- ring buffer: the oldest print is recycled when the pool is full

-- bar layout in the print's local frame (forward is -Z): { x, z, width, length }
local BARS = {
	{ -0.36, 0.12, 0.18, 0.82 }, -- left branch
	{ 0.36, 0.12, 0.18, 0.82 }, -- right branch
	{ 0.0, -0.36, 0.90, 0.18 }, -- toe
}

local TRAIL_COLOR = Color3.fromRGB(86, 58, 38)
local SAND_COLOR = Color3.fromRGB(160, 122, 84)

local function build(): Print
	local parts = {}
	for i = 1, #BARS do
		local p = Instance.new("Part")
		p.Name = "Print"
		p.Anchored = true
		p.CanCollide = false
		p.CanQuery = false
		p.CanTouch = false
		p.CastShadow = false
		p.Material = Enum.Material.SmoothPlastic
		p.Transparency = 1
		p.Parent = folder
		parts[i] = p
	end
	return { parts = parts, born = 0, life = 1, alpha = 0, live = false }
end

-- Stamp one print. `pos` is the hoof position, `yaw` the horse's heading, `front` = bigger fore hoof.
function HoofPrints.stamp(pos: Vector3, yaw: number, front: boolean)
	if not cfg.Enabled then
		return
	end
	local print_ = pool[nextIndex]
	if not print_ then
		print_ = build()
		pool[nextIndex] = print_
	end
	nextIndex = nextIndex % cfg.Max + 1

	local onTrail = TrailMath.onTrail(pos.X, pos.Z)
	local scale = front and 1.0 or 0.88
	local base = CFrame.new(pos.X, pos.Y + 0.17, pos.Z) * CFrame.Angles(0, yaw + (math.random() - 0.5) * 0.12, 0)
	for i, bar in BARS do
		local part = print_.parts[i]
		part.Size = Vector3.new(bar[3] * scale, 0.03, bar[4] * scale)
		part.CFrame = base * CFrame.new(bar[1] * scale, 0, bar[2] * scale)
		part.Color = onTrail and TRAIL_COLOR or SAND_COLOR
	end
	print_.born = os.clock()
	print_.life = onTrail and cfg.Life or cfg.Life * 0.55
	print_.alpha = onTrail and 0.62 or 0.4
	print_.live = true
end

RunService.Heartbeat:Connect(function()
	local now = os.clock()
	for _, p in pool do
		if p.live then
			local t = (now - p.born) / p.life
			if t >= 1 then
				p.live = false
				for _, part in p.parts do
					part.Transparency = 1
				end
			else
				-- hold, then fade out
				local a = p.alpha * (1 - math.max(0, (t - 0.35) / 0.65) ^ 1.5)
				for _, part in p.parts do
					part.Transparency = 1 - a
				end
			end
		end
	end
end)

return HoofPrints
