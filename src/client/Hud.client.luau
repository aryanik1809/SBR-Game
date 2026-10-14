-- Title screen and in-game HUD, all built from code (no image assets needed).
-- Style: Steel Ball Run poster colours (indigo, hot orange, gold, cream) with heavy black ink strokes.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Sfx = require(Shared.Sfx)
local Feel = require(script.Parent.Feel)

local player = Players.LocalPlayer
local playerGui = player:WaitForChild("PlayerGui")

local INK = Color3.fromRGB(14, 8, 20)
local INDIGO = Color3.fromRGB(26, 14, 52)
local GOLD = Color3.fromRGB(255, 204, 64)
local ORANGE = Color3.fromRGB(255, 112, 48)
local MAGENTA = Color3.fromRGB(214, 44, 122)
local CREAM = Color3.fromRGB(250, 238, 208)
local TEAL = Color3.fromRGB(46, 190, 190)

local rng = Random.new()

local function make(class: string, props: { [string]: any }, parent: Instance?): any
	local inst = Instance.new(class)
	for k, v in props do
		inst[k] = v
	end
	inst.Parent = parent
	return inst
end

local function stroke(parent: Instance, thickness: number, color: Color3?): UIStroke
	return make("UIStroke", {
		Thickness = thickness,
		Color = color or INK,
		LineJoinMode = Enum.LineJoinMode.Round,
		ApplyStrokeMode = Enum.ApplyStrokeMode.Contextual,
	}, parent)
end

local function gradient(parent: Instance, top: Color3, bottom: Color3, rotation: number?): UIGradient
	return make("UIGradient", { Color = ColorSequence.new(top, bottom), Rotation = rotation or 90 }, parent)
end

local function label(props: { [string]: any }, parent: Instance): TextLabel
	local base = {
		BackgroundTransparency = 1,
		Font = Enum.Font.GothamBlack,
		TextColor3 = CREAM,
		TextScaled = true,
		RichText = false,
	}
	for k, v in props do
		base[k] = v
	end
	return make("TextLabel", base, parent)
end

local gui = make("ScreenGui", {
	Name = "SBRHud",
	ResetOnSpawn = false,
	IgnoreGuiInset = true,
	DisplayOrder = 20,
	ZIndexBehavior = Enum.ZIndexBehavior.Sibling,
}, playerGui)

local touch = UserInputService.TouchEnabled and not UserInputService.KeyboardEnabled

-- =========================================================================================
-- Speed lines (behind everything else)
-- =========================================================================================
local linesFrame = make("Frame", { Name = "SpeedLines", BackgroundTransparency = 1, Size = UDim2.fromScale(1, 1) }, gui)
local lines = {}
local LINE_COUNT = 26
for i = 1, LINE_COUNT do
	local l = make("Frame", {
		AnchorPoint = Vector2.new(0, 0.5),
		BackgroundColor3 = CREAM,
		BorderSizePixel = 0,
		BackgroundTransparency = 1,
		Size = UDim2.fromOffset(200, 3),
	}, linesFrame)
	make("UIGradient", {
		Transparency = NumberSequence.new({
			NumberSequenceKeypoint.new(0, 1),
			NumberSequenceKeypoint.new(0.35, 0.55),
			NumberSequenceKeypoint.new(1, 0),
		}),
	}, l)
	lines[i] = { frame = l, strength = 0, next = 0 }
end

local function respawnLine(line)
	-- radial line from the screen edge pointing at the centre: x axis of the frame runs outward
	local ang = rng:NextNumber(0, math.pi * 2)
	local cam = workspace.CurrentCamera
	local vp = cam and cam.ViewportSize or Vector2.new(1280, 720)
	local radius = math.min(vp.X, vp.Y) * rng:NextNumber(0.34, 0.50)
	local len = rng:NextNumber(0.16, 0.34) * math.max(vp.X, vp.Y)
	local cx, cy = vp.X / 2, vp.Y / 2
	-- ellipse so lines reach the corners
	local px = cx + math.cos(ang) * radius * (vp.X / vp.Y) * 0.95
	local py = cy + math.sin(ang) * radius
	line.frame.Position = UDim2.fromOffset(px, py)
	line.frame.Rotation = math.deg(ang)
	line.frame.Size = UDim2.fromOffset(len, rng:NextNumber(1.5, 4))
	line.strength = rng:NextNumber(0.3, 0.8)
	line.next = os.clock() + rng:NextNumber(0.05, 0.14)
end
for _, l in lines do
	respawnLine(l)
end

-- =========================================================================================
-- In-game HUD
-- =========================================================================================
local hud = make("CanvasGroup", {
	Name = "Hud",
	BackgroundTransparency = 1,
	Size = UDim2.fromScale(1, 1),
	GroupTransparency = 1,
}, gui)

-- speed card (top left)
local speedCard = make("Frame", {
	Position = UDim2.new(0, 22, 0, 22),
	Size = UDim2.fromOffset(190, 92),
	BackgroundColor3 = INDIGO,
	BackgroundTransparency = 0.12,
}, hud)
make("UICorner", { CornerRadius = UDim.new(0, 10) }, speedCard)
stroke(speedCard, 3, GOLD)
gradient(speedCard, Color3.fromRGB(46, 24, 86), Color3.fromRGB(20, 10, 40))
local speedNum = label({
	Text = "0",
	Position = UDim2.fromOffset(12, 6),
	Size = UDim2.fromOffset(104, 56),
	TextXAlignment = Enum.TextXAlignment.Right,
	TextColor3 = GOLD,
}, speedCard)
stroke(speedNum, 3)
label({
	Text = "MPH",
	Font = Enum.Font.GothamBold,
	Position = UDim2.fromOffset(122, 30),
	Size = UDim2.fromOffset(56, 22),
	TextXAlignment = Enum.TextXAlignment.Left,
	TextColor3 = CREAM,
}, speedCard)
local gaitChip = make("Frame", {
	Position = UDim2.fromOffset(12, 62),
	Size = UDim2.fromOffset(166, 22),
	BackgroundColor3 = ORANGE,
}, speedCard)
make("UICorner", { CornerRadius = UDim.new(0, 5) }, gaitChip)
stroke(gaitChip, 2)
local gaitScale = make("UIScale", {}, gaitChip)
local gaitLabel = label({ Text = "STANDING", Size = UDim2.fromScale(1, 1), TextColor3 = INK, Font = Enum.Font.GothamBlack }, gaitChip)

-- stamina bar (bottom centre)
local bar = make("Frame", {
	AnchorPoint = Vector2.new(0.5, 1),
	Position = UDim2.new(0.5, 0, 1, touch and -150 or -34),
	Size = UDim2.fromOffset(380, 30),
	BackgroundColor3 = INK,
	BackgroundTransparency = 0.15,
}, hud)
make("UICorner", { CornerRadius = UDim.new(0, 8) }, bar)
local barStroke = stroke(bar, 3, GOLD)
local fill = make("Frame", {
	Position = UDim2.fromOffset(4, 4),
	Size = UDim2.new(1, -8, 1, -8),
	BackgroundColor3 = GOLD,
}, bar)
make("UICorner", { CornerRadius = UDim.new(0, 5) }, fill)
local fillGrad = gradient(fill, Color3.fromRGB(255, 226, 120), Color3.fromRGB(255, 120, 40))
label({
	Text = "STAMINA",
	Font = Enum.Font.GothamBold,
	AnchorPoint = Vector2.new(0, 1),
	Position = UDim2.new(0, 6, 0, -4),
	Size = UDim2.fromOffset(110, 16),
	TextXAlignment = Enum.TextXAlignment.Left,
}, bar)
local keyChip = label({
	Text = touch and "HOLD GALLOP" or "SHIFT  GALLOP",
	Font = Enum.Font.GothamBold,
	AnchorPoint = Vector2.new(1, 1),
	Position = UDim2.new(1, -6, 0, -4),
	Size = UDim2.fromOffset(150, 16),
	TextXAlignment = Enum.TextXAlignment.Right,
	TextColor3 = TEAL,
}, bar)

-- controls hint (bottom left), fades after a while
local hint = make("Frame", {
	AnchorPoint = Vector2.new(0, 1),
	Position = UDim2.new(0, 22, 1, -22),
	Size = UDim2.fromOffset(250, 104),
	BackgroundColor3 = INDIGO,
	BackgroundTransparency = 0.25,
	Visible = not touch,
}, hud)
make("UICorner", { CornerRadius = UDim.new(0, 10) }, hint)
stroke(hint, 2, CREAM)
local hintText = label({
	Text = "WASD / ARROWS    RIDE\nSHIFT    GALLOP\nSPACE    JUMP\nQ    REAR UP      E    TOSS HEAD\nM    MUSIC",
	Font = Enum.Font.GothamBold,
	TextScaled = false,
	TextSize = 13,
	TextXAlignment = Enum.TextXAlignment.Left,
	TextYAlignment = Enum.TextYAlignment.Center,
	Size = UDim2.new(1, -20, 1, -8),
	Position = UDim2.fromOffset(12, 4),
}, hint)
local hintStart = 0

local musicLabel = label({
	Text = "M  MUSIC ON",
	Font = Enum.Font.GothamBold,
	TextScaled = false,
	TextSize = 13,
	AnchorPoint = Vector2.new(1, 0),
	Position = UDim2.new(1, -22, 0, 22),
	Size = UDim2.fromOffset(140, 22),
	TextXAlignment = Enum.TextXAlignment.Right,
	Visible = not touch,
}, hud)
stroke(musicLabel, 2)

-- touch buttons
local function touchButton(text: string, pos: UDim2, size: number, color: Color3): TextButton
	local b = make("TextButton", {
		Text = text,
		Font = Enum.Font.GothamBlack,
		TextSize = 14,
		TextColor3 = INK,
		BackgroundColor3 = color,
		AnchorPoint = Vector2.new(1, 1),
		Position = pos,
		Size = UDim2.fromOffset(size, size),
		AutoButtonColor = false,
		Visible = touch,
	}, hud)
	make("UICorner", { CornerRadius = UDim.new(1, 0) }, b)
	stroke(b, 3)
	return b
end
local gallopBtn = touchButton("GALLOP", UDim2.new(1, -150, 1, -30), 84, GOLD)
local rearBtn = touchButton("NEIGH", UDim2.new(1, -250, 1, -30), 64, TEAL)
gallopBtn.InputBegan:Connect(function(input)
	if input.UserInputType == Enum.UserInputType.Touch or input.UserInputType == Enum.UserInputType.MouseButton1 then
		Feel.touchSprint = true
	end
end)
gallopBtn.InputEnded:Connect(function(input)
	if input.UserInputType == Enum.UserInputType.Touch or input.UserInputType == Enum.UserInputType.MouseButton1 then
		Feel.touchSprint = false
	end
end)
rearBtn.Activated:Connect(function()
	Feel.Emote:Fire("rear")
end)

-- gait chip pop
local GAIT_TEXT = { idle = "STANDING", walk = "WALK", trot = "TROT", gallop = "GALLOP" }
local GAIT_COLOR = { idle = CREAM, walk = TEAL, trot = GOLD, gallop = ORANGE }
Feel.GaitChanged.Event:Connect(function(gait: string)
	local name = GAIT_TEXT[gait] or gait
	if gait == "trot" then
		name = "CANTER"
	end
	gaitLabel.Text = name
	gaitChip.BackgroundColor3 = GAIT_COLOR[gait] or GOLD
	gaitScale.Scale = 1.35
	TweenService:Create(gaitScale, TweenInfo.new(0.35, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()
end)

-- big "GO GO GO" pops when a gallop starts
local function popKana()
	local cam = workspace.CurrentCamera
	local vp = cam and cam.ViewportSize or Vector2.new(1280, 720)
	for i = 1, 6 do
		local side = i % 2 == 0 and 1 or -1
		local t = label({
			Text = "ゴ",
			TextScaled = false,
			TextSize = rng:NextInteger(54, 96),
			Font = Enum.Font.GothamBlack,
			TextColor3 = i % 3 == 0 and MAGENTA or ORANGE,
			AnchorPoint = Vector2.new(0.5, 0.5),
			Size = UDim2.fromOffset(100, 100),
			Position = UDim2.fromOffset(vp.X * (0.5 + side * rng:NextNumber(0.22, 0.44)), vp.Y * rng:NextNumber(0.2, 0.8)),
			Rotation = rng:NextNumber(-18, 18),
			TextTransparency = 0,
			ZIndex = 5,
		}, gui)
		local s = stroke(t, 5)
		local sc = make("UIScale", { Scale = 0.3 }, t)
		TweenService:Create(sc, TweenInfo.new(0.22, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()
		task.delay(0.35 + i * 0.03, function()
			local info = TweenInfo.new(0.5, Enum.EasingStyle.Quad)
			TweenService:Create(t, info, { TextTransparency = 1, Position = t.Position + UDim2.fromOffset(side * 40, -30) }):Play()
			TweenService:Create(s, info, { Transparency = 1 }):Play()
			task.delay(0.55, function()
				t:Destroy()
			end)
		end)
	end
end
Feel.SprintBurst.Event:Connect(function()
	if Config.Fx.SpeedLines then
		popKana()
	end
end)

-- =========================================================================================
-- Title screen
-- =========================================================================================
local title = make("Frame", { Name = "Title", BackgroundTransparency = 1, Size = UDim2.fromScale(1, 1), ZIndex = 10 }, gui)

local dim = make("Frame", { BackgroundColor3 = INDIGO, BackgroundTransparency = 0.3, Size = UDim2.fromScale(1, 1), BorderSizePixel = 0, ZIndex = 10 }, title)
make("UIGradient", {
	Rotation = 90,
	Transparency = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 0.15),
		NumberSequenceKeypoint.new(0.45, 0.62),
		NumberSequenceKeypoint.new(0.75, 0.55),
		NumberSequenceKeypoint.new(1, 0.1),
	}),
}, dim)

local barTop = make("Frame", { BackgroundColor3 = Color3.new(0, 0, 0), BorderSizePixel = 0, Size = UDim2.fromScale(1, 0.1), ZIndex = 12 }, title)
local barBottom = make("Frame", {
	BackgroundColor3 = Color3.new(0, 0, 0),
	BorderSizePixel = 0,
	AnchorPoint = Vector2.new(0, 1),
	Position = UDim2.fromScale(0, 1),
	Size = UDim2.fromScale(1, 0.1),
	ZIndex = 12,
}, title)

local logo = make("CanvasGroup", {
	BackgroundTransparency = 1,
	AnchorPoint = Vector2.new(0.5, 0.5),
	Position = UDim2.fromScale(0.5, 0.40),
	Size = UDim2.fromScale(0.74, 0.46),
	ZIndex = 13,
}, title)
local logoScale = make("UIScale", {}, logo)

-- menacing katakana drifting behind the logo
local kana = {}
for i = 1, 9 do
	local k = label({
		Text = "ゴ",
		TextScaled = false,
		TextSize = rng:NextInteger(44, 88),
		TextColor3 = i % 2 == 0 and MAGENTA or Color3.fromRGB(120, 56, 190),
		TextTransparency = 0.25,
		AnchorPoint = Vector2.new(0.5, 0.5),
		Size = UDim2.fromOffset(90, 90),
		Position = UDim2.fromScale(0.05 + (i - 1) * 0.112, rng:NextNumber(0.1, 0.9)),
		Rotation = rng:NextNumber(-14, 14),
		ZIndex = 11,
	}, logo)
	stroke(k, 4)
	kana[i] = { label = k, base = k.Position, phase = rng:NextNumber(0, 6.28) }
end

local steel = label({
	Text = "STEEL BALL",
	Font = Enum.Font.GothamBlack,
	AnchorPoint = Vector2.new(0.5, 0),
	Position = UDim2.fromScale(0.5, 0.05),
	Size = UDim2.fromScale(0.86, 0.34),
	TextColor3 = Color3.new(1, 1, 1),
	Rotation = -3,
	ZIndex = 14,
}, logo)
stroke(steel, 9)
gradient(steel, Color3.fromRGB(255, 236, 140), Color3.fromRGB(255, 128, 40))
local runLabel = label({
	Text = "RUN",
	Font = Enum.Font.GothamBlack,
	AnchorPoint = Vector2.new(0.5, 0),
	Position = UDim2.fromScale(0.5, 0.34),
	Size = UDim2.fromScale(0.52, 0.44),
	TextColor3 = Color3.new(1, 1, 1),
	Rotation = -3,
	ZIndex = 14,
}, logo)
stroke(runLabel, 10)
gradient(runLabel, Color3.fromRGB(255, 120, 190), Color3.fromRGB(190, 40, 120))
label({
	Text = "THE GREAT AMERICAN HORSE RACE  -  1890",
	Font = Enum.Font.Antique,
	AnchorPoint = Vector2.new(0.5, 0),
	Position = UDim2.fromScale(0.5, 0.85),
	Size = UDim2.fromScale(0.78, 0.09),
	TextColor3 = CREAM,
	ZIndex = 14,
}, logo)

local prompt = label({
	Text = touch and "TAP TO RIDE" or "PRESS ANY KEY  -  CLICK  -  TAP",
	Font = Enum.Font.GothamBlack,
	AnchorPoint = Vector2.new(0.5, 1),
	Position = UDim2.fromScale(0.5, 0.86),
	Size = UDim2.fromOffset(520, 34),
	ZIndex = 14,
}, title)
stroke(prompt, 4)

local noAudio = Sfx.status()
if noAudio == 0 then
	label({
		Text = "No audio uploaded yet - run tools/upload_audio.py (see docs/audio.md)",
		Font = Enum.Font.GothamMedium,
		TextScaled = false,
		TextSize = 12,
		TextColor3 = Color3.fromRGB(190, 180, 200),
		AnchorPoint = Vector2.new(0.5, 1),
		Position = UDim2.new(0.5, 0, 0.9, -6),
		Size = UDim2.fromOffset(520, 18),
		ZIndex = 14,
	}, title)
end

local flash = make("Frame", { BackgroundColor3 = Color3.new(1, 1, 1), BackgroundTransparency = 1, Size = UDim2.fromScale(1, 1), BorderSizePixel = 0, ZIndex = 30 }, gui)

local function start()
	if Feel.started then
		return
	end
	Feel.start()
	hintStart = os.clock()
	flash.BackgroundTransparency = 0.25
	TweenService:Create(flash, TweenInfo.new(0.6, Enum.EasingStyle.Quad), { BackgroundTransparency = 1 }):Play()
	Feel.impulse(0.7, 5)
	local info = TweenInfo.new(0.9, Enum.EasingStyle.Quad, Enum.EasingDirection.In)
	TweenService:Create(logo, info, { GroupTransparency = 1 }):Play()
	TweenService:Create(logoScale, info, { Scale = 1.35 }):Play()
	TweenService:Create(dim, TweenInfo.new(1.4), { BackgroundTransparency = 1 }):Play()
	TweenService:Create(prompt, TweenInfo.new(0.3), { TextTransparency = 1 }):Play()
	TweenService:Create(barTop, TweenInfo.new(1.1, Enum.EasingStyle.Quart), { Size = UDim2.fromScale(1, 0) }):Play()
	TweenService:Create(barBottom, TweenInfo.new(1.1, Enum.EasingStyle.Quart), { Size = UDim2.fromScale(1, 0) }):Play()
	TweenService:Create(hud, TweenInfo.new(1.2), { GroupTransparency = 0 }):Play()
	task.delay(1.6, function()
		title:Destroy()
	end)
end

UserInputService.InputBegan:Connect(function(input)
	if Feel.started then
		return
	end
	local t = input.UserInputType
	if t == Enum.UserInputType.Keyboard or t == Enum.UserInputType.MouseButton1 or t == Enum.UserInputType.Touch
		or t == Enum.UserInputType.Gamepad1 then
		start()
	end
end)

-- =========================================================================================
-- per-frame
-- =========================================================================================
local shownSpeed = 0
RunService.RenderStepped:Connect(function(dt)
	local now = os.clock()

	-- title animation
	if title.Parent then
		prompt.TextTransparency = Feel.started and 1 or (0.15 + 0.35 * (0.5 + 0.5 * math.sin(now * 3.2)))
		for _, k in kana do
			local sx = math.sin(now * 17 + k.phase) * 4
			local sy = math.cos(now * 15 + k.phase * 1.7) * 4
			k.label.Position = k.base + UDim2.fromOffset(sx, sy)
			k.label.TextTransparency = 0.2 + 0.25 * (0.5 + 0.5 * math.sin(now * 2.5 + k.phase))
		end
		if not Feel.started then
			logo.Rotation = math.sin(now * 0.8) * 0.8
			logoScale.Scale = 1 + math.sin(now * 1.6) * 0.012
		end
	end

	-- speed readout (studs/s -> mph at ~0.28 m per stud)
	shownSpeed = shownSpeed + (Feel.speed - shownSpeed) * (1 - math.exp(-10 * dt))
	speedNum.Text = tostring(math.floor(shownSpeed * 0.626 + 0.5))

	-- stamina bar
	local s = Feel.stamina
	fill.Size = UDim2.new(s, -8 * s, 1, -8)
	if Feel.exhausted then
		fill.BackgroundColor3 = Color3.fromRGB(220, 50, 60)
		fillGrad.Enabled = false
		barStroke.Color = Color3.fromRGB(220, 50, 60)
		bar.Position = UDim2.new(0.5, math.sin(now * 60) * 2, 1, touch and -150 or -34)
	else
		fillGrad.Enabled = true
		fill.BackgroundColor3 = Color3.new(1, 1, 1)
		barStroke.Color = (s < 0.3) and ORANGE or GOLD
		bar.Position = UDim2.new(0.5, 0, 1, touch and -150 or -34)
	end
	keyChip.TextColor3 = Feel.sprinting and ORANGE or TEAL

	-- controls hint fades out after a while
	if Feel.started and hintStart > 0 then
		local age = now - hintStart
		local a = math.clamp((age - 16) / 3, 0, 1)
		hint.BackgroundTransparency = 0.25 + 0.75 * a
		hintText.TextTransparency = a
		if hint:FindFirstChildOfClass("UIStroke") then
			(hint:FindFirstChildOfClass("UIStroke") :: UIStroke).Transparency = a
		end
	end

	-- speed lines
	local strength = 0
	if Config.Fx.SpeedLines and Feel.started then
		strength = math.clamp((Feel.speedRatio - 0.5) / 0.4, 0, 1) * (Feel.sprinting and 1 or 0.45)
	end
	for _, line in lines do
		if now > line.next then
			respawnLine(line)
		end
		line.frame.BackgroundTransparency = 1 - strength * line.strength
	end
end)

-- music mute toggle
local musicOn = true
UserInputService.InputBegan:Connect(function(input, processed)
	if processed then
		return
	end
	if input.KeyCode == Enum.KeyCode.M then
		musicOn = not musicOn
		Sfx.setGroupVolume("Music", musicOn and Config.Audio.Music or 0, 0.4)
		musicLabel.Text = musicOn and "M  MUSIC ON" or "M  MUSIC OFF"
		Sfx.play("ui_click", { volume = 0.5 })
	end
end)
