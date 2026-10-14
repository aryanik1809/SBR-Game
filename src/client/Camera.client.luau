-- Fixed-angle follow camera. In play it never rotates, so WASD always means up/down/left/right on screen.
-- On top of that it breathes with the ride: pulls back and widens at a gallop, looks a little ahead of
-- the horse, shakes on landings and hard running, and swoops in from a title-screen orbit.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local SpriteFactory = require(Shared.SpriteFactory)
local Feel = require(script.Parent.Feel)

local player = Players.LocalPlayer
local camera = workspace.CurrentCamera
local settings = Config.Camera
local feel = Config.Feel
local toCamera = SpriteFactory.cameraNormal()

local focus: Vector3? = nil
local lead = Vector3.zero
local seed = math.random() * 100

local function smoothstep(x: number): number
	x = math.clamp(x, 0, 1)
	return x * x * (3 - 2 * x)
end

RunService:BindToRenderStep("SBRCamera", Enum.RenderPriority.Camera.Value + 1, function(dt)
	camera.CameraType = Enum.CameraType.Scriptable

	local character = player.Character
	local root = character and character:FindFirstChild("HumanoidRootPart")
	if not root then
		return
	end

	-- the rider's chest is a bit above the (invisible) root part
	local target = (root :: BasePart).Position + Vector3.new(0, 1.5, 0)
	if focus == nil then
		focus = target
	else
		-- Frame-rate independent smoothing.
		local alpha = 1 - math.pow(settings.Smoothing, dt * 6)
		focus = focus:Lerp(target, alpha)
	end

	-- title -> gameplay blend
	if Feel.started then
		Feel.introAlpha = math.min(1, Feel.introAlpha + dt / feel.IntroSeconds)
	else
		Feel.titleTime += dt
	end
	local a = smoothstep(Feel.introAlpha)

	-- gameplay camera: pulled back, widened and led ahead as speed rises
	local ratio = Feel.speedRatio
	local flatVel = Vector3.new(Feel.velocity.X, 0, Feel.velocity.Z)
	lead = lead:Lerp(flatVel * feel.LeadAhead, 1 - math.exp(-2.2 * dt))
	local dist = settings.Distance + feel.ZoomOutAtGallop * ratio * ratio
	local fov = settings.FieldOfView + feel.FovAtGallop * ratio + Feel.fovKick
	local f = (focus :: Vector3) + lead
	local gameCF = CFrame.lookAt(f + toCamera * dist, f)

	-- title camera: a slow, low sweep around the horse
	local sway = math.sin(Feel.titleTime * 0.22) * 0.55
	local pitch = math.rad(feel.TitlePitch)
	local offset = Vector3.new(math.sin(-0.5 + sway) * math.cos(pitch), math.sin(pitch), math.cos(-0.5 + sway) * math.cos(pitch))
		* feel.TitleDistance
	local titleCF = CFrame.lookAt(target + Vector3.new(0, 1.5, 0) + offset, target + Vector3.new(0, 2.6, 0))

	local cf = titleCF:Lerp(gameCF, a)
	camera.FieldOfView = feel.TitleFov + (fov - feel.TitleFov) * a

	-- shake: a constant tremble at a gallop plus decaying impulses from landings and bursts
	local shake = Feel.shake + feel.ShakeAtGallop * ratio * ratio * (Feel.sprinting and 1 or 0.35)
	if shake > 0.001 then
		local t = os.clock() * 26
		local dx = math.noise(t, seed) * shake
		local dy = math.noise(seed, t) * shake
		cf = cf * CFrame.new(dx, dy, 0) * CFrame.Angles(0, 0, math.noise(t, seed + 9) * shake * 0.012)
	end
	Feel.shake *= math.exp(-6 * dt)
	Feel.fovKick *= math.exp(-4 * dt)

	camera.CFrame = cf
end)
