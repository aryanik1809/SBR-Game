-- Screen grading and bloom, client-side only (the world and its lighting are untouched).
-- Gets punchier as you speed up. Turn off with Config.Fx.PostProcessing = false.
local Lighting = game:GetService("Lighting")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Feel = require(script.Parent.Feel)

if not Config.Fx.PostProcessing then
	return
end

local grade = Instance.new("ColorCorrectionEffect")
grade.Name = "SBRGrade"
grade.TintColor = Color3.fromRGB(255, 244, 228)
grade.Parent = Lighting

local bloom = Instance.new("BloomEffect")
bloom.Name = "SBRBloom"
bloom.Size = 26
bloom.Threshold = 0.92
bloom.Parent = Lighting

RunService.RenderStepped:Connect(function(dt)
	local r = Feel.speedRatio * (Feel.sprinting and 1 or 0.5)
	local intro = Feel.introAlpha
	local k = 1 - math.exp(-6 * dt)
	-- the title screen is slightly moodier; gameplay warms up and gains contrast with speed
	local targetSat = (0.04 + 0.10 * intro) + 0.10 * r
	local targetContrast = (0.10 + 0.04 * intro) + 0.08 * r
	local targetBright = -0.03 * (1 - intro) + 0.01 * r
	grade.Saturation += (targetSat - grade.Saturation) * k
	grade.Contrast += (targetContrast - grade.Contrast) * k
	grade.Brightness += (targetBright - grade.Brightness) * k
	bloom.Intensity += ((0.22 + 0.30 * r + 0.15 * Feel.fovKick / 5) - bloom.Intensity) * k
end)
