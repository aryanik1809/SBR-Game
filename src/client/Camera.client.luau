-- Fixed-angle follow camera. Never rotates, so WASD always means up/down/left/right on screen.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Config = require(ReplicatedStorage:WaitForChild("Shared").Config)
local SpriteFactory = require(ReplicatedStorage.Shared.SpriteFactory)

local player = Players.LocalPlayer
local camera = workspace.CurrentCamera
local settings = Config.Camera
local toCamera = SpriteFactory.cameraNormal() * settings.Distance

local focus: Vector3? = nil

RunService:BindToRenderStep("SBRCamera", Enum.RenderPriority.Camera.Value + 1, function(dt)
	camera.CameraType = Enum.CameraType.Scriptable
	camera.FieldOfView = settings.FieldOfView

	local character = player.Character
	local root = character and character:FindFirstChild("HumanoidRootPart")
	if not root then
		return
	end

	local target = (root :: BasePart).Position
	if focus == nil then
		focus = target
	else
		-- Frame-rate independent smoothing.
		local alpha = 1 - math.pow(settings.Smoothing, dt * 6)
		focus = focus:Lerp(target, alpha)
	end

	camera.CFrame = CFrame.lookAt(focus + toCamera, focus)
end)
