-- Gives every player a horse and rider, drives their animation from how the (invisible) Humanoid
-- character actually moves, and handles the local player's riding controls:
--   * momentum: the horse accelerates and brakes instead of snapping to speed
--   * Shift (or the on-screen button) = gallop, which burns stamina
--   * Space = jump, Q = rear up and neigh, E = toss head and snort
-- Everything visual is built on the client, so other players' horses cost the server nothing.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Gait = require(Shared.Gait)
local HorseAnimator = require(Shared.HorseAnimator)
local HorseModel = require(Shared.HorseModel)
local Sfx = require(Shared.Sfx)
local Feel = require(script.Parent.Feel)
local HoofPrints = require(script.Parent.HoofPrints)

local player = Players.LocalPlayer
local mountCfg = Config.Mount
local sat = Gait.sat

local folder = Instance.new("Folder")
folder.Name = "Mounts"
folder.Parent = workspace

local mounts: { [Player]: any } = {}

-- Raycasts for the ground must ignore horses and characters.
local rayParams = RaycastParams.new()
rayParams.FilterType = Enum.RaycastFilterType.Exclude
local filterDirty = true
local function refreshFilter()
	local list: { Instance } = { folder }
	for _, p in Players:GetPlayers() do
		if p.Character then
			table.insert(list, p.Character)
		end
	end
	rayParams.FilterDescendantsInstances = list
	filterDirty = false
end

local function anchorPart(name: string): Part
	local p = Instance.new("Part")
	p.Name = name
	p.Size = Vector3.new(0.4, 0.4, 0.4)
	p.Transparency = 1
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.CastShadow = false
	p.Parent = folder
	return p
end

local function dustEmitter(parent: Instance, big: boolean): ParticleEmitter
	local e = Instance.new("ParticleEmitter")
	e.Texture = "rbxasset://textures/particles/smoke_main.dds"
	e.Color = ColorSequence.new(Color3.fromRGB(232, 204, 160), Color3.fromRGB(190, 152, 112))
	e.Size = NumberSequence.new({
		NumberSequenceKeypoint.new(0, big and 1.0 or 0.6),
		NumberSequenceKeypoint.new(1, big and 5.0 or 3.2),
	})
	e.Transparency = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 0.55),
		NumberSequenceKeypoint.new(0.6, 0.8),
		NumberSequenceKeypoint.new(1, 1),
	})
	e.Lifetime = NumberRange.new(0.5, big and 1.4 or 1.0)
	e.Speed = NumberRange.new(2, big and 9 or 6)
	e.SpreadAngle = Vector2.new(40, 40)
	e.Acceleration = Vector3.new(0, 3, 0)
	e.Drag = 2.5
	e.Rotation = NumberRange.new(0, 360)
	e.RotSpeed = NumberRange.new(-70, 70)
	e.LightInfluence = 0.5
	e.Rate = 0
	e.EmissionDirection = Enum.NormalId.Top
	e.Parent = parent
	return e
end

local function destroyMount(plr: Player)
	local rec = mounts[plr]
	if not rec then
		return
	end
	mounts[plr] = nil
	rec.rig:destroy()
	for _, d in rec.dust do
		d.part:Destroy()
	end
	rec.trail:Destroy()
	rec.shadow:Destroy()
	rec.headPart:Destroy()
	rec.bodyPart:Destroy()
end

local function createMount(plr: Player, character: Model)
	local hrp = character:WaitForChild("HumanoidRootPart", 10)
	local hum = character:WaitForChild("Humanoid", 10)
	if not hrp or not hum then
		return
	end
	destroyMount(plr)
	filterDirty = true

	local isLocal = plr == player
	local rec: any = { plr = plr, char = character, hrp = hrp, hum = hum, isLocal = isLocal }
	HorseModel.ColorScale = mountCfg.ColorScale or 1
	rec.rig = HorseModel.new({ seed = plr.UserId % 9973 })
	rec.rig:step(CFrame.new(hrp.Position - Vector3.new(0, 3, 0)))
	rec.rig.model.Parent = folder
	rec.dust = {}
	for leg in HorseModel.Legs do
		local part = anchorPart("Dust" .. leg)
		rec.dust[leg] = { part = part, emitter = dustEmitter(part, false) }
	end
	rec.trailPart = anchorPart("DustTrail")
	rec.trail = rec.trailPart
	rec.trailEmitter = dustEmitter(rec.trailPart, true)
	-- a slow, lingering cloud hanging in the air where a galloping rider has passed
	rec.cloudEmitter = dustEmitter(rec.trailPart, true)
	rec.cloudEmitter.Lifetime = NumberRange.new(1.6, 2.8)
	rec.cloudEmitter.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 2.0), NumberSequenceKeypoint.new(1, 9.5) })
	rec.cloudEmitter.Transparency = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 0.72),
		NumberSequenceKeypoint.new(0.5, 0.86),
		NumberSequenceKeypoint.new(1, 1),
	})
	rec.cloudEmitter.Speed = NumberRange.new(0.5, 3)
	rec.cloudEmitter.Acceleration = Vector3.new(0, 1.2, 0)
	rec.headPart = anchorPart("HeadSound")
	rec.bodyPart = anchorPart("BodySound")

	local shadow = Instance.new("Part")
	shadow.Name = "Shadow"
	shadow.Shape = Enum.PartType.Cylinder
	shadow.Size = Vector3.new(0.05, 5.4, 12.5)
	shadow.Color = Color3.new(0, 0, 0)
	shadow.Material = Enum.Material.SmoothPlastic
	shadow.Transparency = 0.6
	shadow.Anchored = true
	shadow.CanCollide = false
	shadow.CanQuery = false
	shadow.CanTouch = false
	shadow.CastShadow = false
	shadow.Parent = folder
	rec.shadow = shadow

	rec.lastPos = hrp.Position
	rec.vel = Vector3.zero
	rec.yaw = 0
	rec.yawRate = 0
	rec.prevSpeed = 0
	rec.decel = 0
	rec.gait = "idle"
	rec.lastJingle = 0
	rec.lastBreath = os.clock() + math.random() * 3
	rec.skidCooldown = 0
	rec.baseHeight = nil

	local rig = rec.rig
	local function near(): number
		-- cheap distance fade so a crowd of horses doesn't spam sounds
		local cam = workspace.CurrentCamera
		if isLocal or not cam then
			return 1
		end
		return 1 - sat((cam.CFrame.Position - hrp.Position).Magnitude / 220)
	end

	rec.anim = HorseAnimator.new(rig, {
		seed = plr.UserId % 9973,
		onStep = function(leg: string, strength: number, hoofPos: Vector3)
			local d = rec.dust[leg]
			local falloff = near()
			if falloff <= 0.05 then
				return
			end
			d.emitter:Emit(math.floor(1 + strength * 4))
			if falloff > 0.2 and rec.anim.speed > 3 then
				HoofPrints.stamp(hoofPos, rec.yaw, leg:sub(1, 1) == "F")
			end
			local walking = rec.anim.gait == "walk"
			Sfx.variant(walking and "hoof_soft" or "hoof_dirt", 4, {
				parent = d.part,
				volume = (0.4 + 0.45 * strength) * (isLocal and 1 or 0.75) * falloff,
				pitch = walking and 0.95 or 1.0,
				jitter = 0.07,
			})
			local now = os.clock()
			if strength > 0.2 and now - rec.lastJingle > 0.45 and math.random() < 0.3 then
				rec.lastJingle = now
				Sfx.variant("jingle", 2, { parent = rec.bodyPart, volume = 0.32 + 0.2 * strength, jitter = 0.1 })
			elseif math.random() < 0.05 then
				Sfx.variant("creak", 2, { parent = rec.bodyPart, volume = 0.3, jitter = 0.12 })
			end
		end,
		onLand = function(strength: number)
			for _, d in rec.dust do
				d.emitter:Emit(4 + math.floor(strength * 8))
			end
			Sfx.play("land", { parent = rec.bodyPart, volume = 0.45 + 0.7 * strength, jitter = 0.08 })
			if isLocal then
				Feel.impulse(0.25 + 0.6 * strength, 1.5)
			end
		end,
		onEmote = function(name: string)
			if name == "whinny" then
				Sfx.variant("whinny", 3, { parent = rec.headPart, volume = isLocal and 1 or 0.8, jitter = 0.05 })
			elseif name == "snort" then
				Sfx.variant("snort", 2, { parent = rec.headPart, volume = 0.8, jitter = 0.08 })
			elseif name == "nicker" then
				Sfx.play("nicker", { parent = rec.headPart, volume = 0.8, jitter = 0.06 })
			end
		end,
	})

	if isLocal then
		rec.control = { dir = Vector3.zero, maxSpeed = mountCfg.CanterSpeed, stamina = mountCfg.Stamina.Max, regenAt = 0, sprinting = false }
		hum.StateChanged:Connect(function(_, new)
			if new == Enum.HumanoidStateType.Jumping and Feel.started then
				Sfx.play("jump", { parent = rec.bodyPart, volume = 0.6, jitter = 0.1 })
				if math.random() < 0.35 then
					Sfx.play("snort_2", { parent = rec.headPart, volume = 0.5 })
				end
			end
		end)
	end
	-- Bumping into another rider: the server gives every character an invisible "MountBody" block, so
	-- horses collide for real; here we just react to a hard hit with sound, a flinch and a camera jolt.
	if isLocal then
		local body = character:WaitForChild("MountBody", 5)
		if body then
			local lastBump = 0
			body.Touched:Connect(function(other)
				if other.Name ~= "MountBody" or other.Parent == character then
					return
				end
				local now = os.clock()
				if now - lastBump < 0.7 or not Feel.started then
					return
				end
				local otherRoot = other.Parent and other.Parent:FindFirstChild("HumanoidRootPart")
				local otherVel = otherRoot and otherRoot.AssemblyLinearVelocity or Vector3.zero
				local rel = (rec.vel - otherVel).Magnitude
				if rel < 7 then
					return -- just brushing past
				end
				lastBump = now
				local strength = sat(rel / 40)
				Sfx.play("bump", { parent = rec.bodyPart, volume = 0.5 + 0.6 * strength, jitter = 0.08 })
				if math.random() < 0.5 then
					Sfx.variant("whinny", 3, { parent = rec.headPart, volume = 0.55, delay = 0.12, jitter = 0.06 })
				end
				rec.anim:toss("snort")
				for _, d in rec.dust do
					d.emitter:Emit(3 + math.floor(strength * 5))
				end
				Feel.impulse(0.15 + 0.5 * strength, 2.5 * strength)
			end)
		end
	end
	mounts[plr] = rec
end

-- ---- local controls ---------------------------------------------------------------------------------
local function sprintHeld(): boolean
	if Feel.touchSprint then
		return true
	end
	if UserInputService:IsKeyDown(Enum.KeyCode.LeftShift) or UserInputService:IsKeyDown(Enum.KeyCode.RightShift) then
		return true
	end
	return UserInputService:IsGamepadButtonDown(Enum.UserInputType.Gamepad1, Enum.KeyCode.ButtonR2)
		or UserInputService:IsGamepadButtonDown(Enum.UserInputType.Gamepad1, Enum.KeyCode.ButtonA)
end

local function control(rec, dt: number)
	local hum: Humanoid = rec.hum
	local c = rec.control
	if not Feel.started then
		-- title screen: stand still
		hum.WalkSpeed = 0
		hum.JumpHeight = 0
		hum:Move(Vector3.zero, false)
		return
	end
	hum.JumpHeight = mountCfg.JumpHeight
	hum.UseJumpPower = false

	-- raw input direction for this frame (set by Roblox's control module just before us)
	local raw = hum.MoveDirection
	local moving = raw.Magnitude > 0.1
	local st = mountCfg.Stamina
	local now = os.clock()

	-- stamina + gallop
	local want = sprintHeld() and moving
	if c.exhausted and c.stamina >= st.MinToSprint then
		c.exhausted = false
		Sfx.play("stamina_ready", { volume = 0.6 })
	end
	if want and not c.exhausted and c.stamina > 0 then
		if not c.sprinting then
			c.sprinting = true
			rec.anim:burst(1)
			Feel.impulse(0.4, 3)
			Feel.SprintBurst:Fire()
			Sfx.play("whip_crack", { volume = 0.9, jitter = 0.05 })
			Sfx.play("whoosh_boost", { volume = 0.6 })
			Sfx.play("gallop_burst", { parent = rec.bodyPart, volume = 0.8 })
			-- kick up a puff as the horse digs in
			rec.trailEmitter:Emit(20)
			for _, d in rec.dust do
				d.emitter:Emit(7)
			end
			if math.random() < 0.6 then
				Sfx.variant("whinny", 3, { parent = rec.headPart, volume = 0.9, delay = 0.15 })
			end
		end
		c.stamina = math.max(0, c.stamina - st.Drain * dt)
		c.regenAt = now + st.RegenDelay
		if c.stamina <= 0 then
			c.exhausted = true
			c.sprinting = false
			Sfx.play("pant", { parent = rec.headPart, volume = 0.9 })
			Sfx.play("snort_1", { parent = rec.headPart, volume = 0.6, delay = 0.6 })
		end
	else
		c.sprinting = false
		if now >= c.regenAt then
			c.stamina = math.min(st.Max, c.stamina + st.Regen * dt)
		end
	end
	Feel.sprinting = c.sprinting
	Feel.exhausted = c.exhausted == true
	Feel.stamina = c.stamina / st.Max

	-- speed ceiling eases between canter and gallop
	local topSpeed = c.sprinting and mountCfg.GallopSpeed or mountCfg.CanterSpeed
	c.maxSpeed = Gait.damp(c.maxSpeed, topSpeed, c.sprinting and 2.4 or 3.2, dt)
	hum.WalkSpeed = c.maxSpeed

	-- momentum: steer the move direction through a low-pass filter. A 180 degree turn passes through
	-- zero, so the horse naturally slows down to swing around, then picks up speed again.
	local rate = raw.Magnitude >= c.dir.Magnitude and mountCfg.Accel or mountCfg.Brake
	c.dir = c.dir:Lerp(raw, 1 - math.exp(-rate * dt))
	if c.dir.Magnitude < 0.02 and not moving then
		c.dir = Vector3.zero
	end
	hum:Move(c.dir, false)
end

UserInputService.InputBegan:Connect(function(input, processed)
	if processed or not Feel.started then
		return
	end
	if input.KeyCode == Enum.KeyCode.Q then
		Feel.Emote:Fire("rear")
	elseif input.KeyCode == Enum.KeyCode.E then
		Feel.Emote:Fire("toss")
	end
end)

Feel.Emote.Event:Connect(function(name: string)
	local rec = mounts[player]
	if not rec or not Feel.started then
		return
	end
	if name == "rear" then
		if rec.anim:rear() then
			Feel.impulse(0.2, 0)
		end
	elseif name == "toss" then
		rec.anim:toss(math.random() < 0.5 and "snort" or "nicker")
	end
end)

-- ---- per-frame update -------------------------------------------------------------------------------
local function updateMount(rec, dt: number)
	local hrp: BasePart = rec.hrp
	local pos = hrp.Position

	if filterDirty then
		refreshFilter()
	end
	local hit = workspace:Raycast(pos, Vector3.new(0, -30, 0), rayParams)
	local groundY = hit and hit.Position.Y or (pos.Y - 3)
	local height = pos.Y - groundY
	rec.baseHeight = rec.baseHeight and math.min(rec.baseHeight, height) or height
	local grounded = height < rec.baseHeight + 0.8

	-- velocity from actual movement (works the same for remote players)
	local rawVel = (pos - rec.lastPos) / math.max(dt, 1e-3)
	rec.lastPos = pos
	if rawVel.Magnitude > 150 then
		rawVel = Vector3.zero -- teleport / respawn
		rec.vel = Vector3.zero
	end
	rec.vel = rec.vel:Lerp(rawVel, 1 - math.exp(-14 * dt))
	local flat = Vector3.new(rec.vel.X, 0, rec.vel.Z)
	local speed = flat.Magnitude
	if speed < 0.25 then
		speed = 0
	end

	-- facing: turn smoothly toward the direction of travel
	local yawRate = 0
	if speed > 1.2 then
		local target = math.atan2(-flat.X, -flat.Z)
		local diff = ((target - rec.yaw + math.pi) % (2 * math.pi)) - math.pi
		local step = diff * (1 - math.exp(-8 * dt))
		local maxStep = 7.5 * dt
		step = math.clamp(step, -maxStep, maxStep)
		rec.yaw += step
		yawRate = step / math.max(dt, 1e-3)
	end

	-- braking: a hard drop from a fast gait
	local decel = (rec.prevSpeed - speed) / math.max(dt, 1e-3)
	rec.decel = Gait.damp(rec.decel, decel, 8, dt)
	local braking = (rec.prevSpeed > 14) and sat((rec.decel - 28) / 50) or 0
	if braking > 0.55 and os.clock() > rec.skidCooldown and rec.prevSpeed > 20 then
		rec.skidCooldown = os.clock() + 1.2
		Sfx.play("skid", { parent = rec.bodyPart, volume = 0.8, jitter = 0.05 })
		for _, leg in { "FL", "FR" } do
			rec.dust[leg].emitter:Emit(10)
		end
		if rec.isLocal then
			Feel.impulse(0.12, 0)
		end
	end
	rec.prevSpeed = speed

	local rootCF = CFrame.new(pos.X, groundY, pos.Z) * CFrame.Angles(0, rec.yaw, 0)
	local adjust = rec.anim:update(dt, {
		speed = speed,
		yawRate = yawRate,
		grounded = grounded,
		vy = rec.vel.Y,
		braking = braking,
		velocity = rec.vel,
	})
	-- when airborne the character is already off the ground, so the rig simply follows it
	rec.rig:step(rootCF * adjust)

	-- helpers that follow the rig: dust under each hoof, sound emitters, shadow
	for leg, d in rec.dust do
		d.part.Position = rec.rig:hoofWorld(leg)
	end
	rec.bodyPart.Position = rootCF.Position + Vector3.new(0, 3, 0)
	rec.headPart.Position = (rec.rig:boneWorld("Head") :: CFrame).Position
	local back = rootCF * Vector3.new(0, 1.2, 4.6)
	rec.trailPart.Position = Vector3.new(back.X, groundY + 0.4, back.Z)
	rec.trailEmitter.Rate = speed > 15 and (4 + 26 * sat((speed - 15) / 22)) or 0
	rec.cloudEmitter.Rate = speed > 24 and (2 + 10 * sat((speed - 24) / 12)) or 0
	local lift = sat((height - rec.baseHeight) / 7)
	rec.shadow.CFrame = CFrame.new(pos.X, groundY + 0.12, pos.Z) * CFrame.Angles(0, rec.yaw, math.pi / 2)
	rec.shadow.Transparency = 0.58 + 0.38 * lift

	-- ambient horse sounds
	local now = os.clock()
	if now > rec.lastBreath and rec.anim then
		local moving = speed > 12
		rec.lastBreath = now + (moving and (1.1 + math.random() * 0.8) or (4 + math.random() * 4))
		Sfx.variant("breath", 2, {
			parent = rec.headPart,
			volume = (moving and 0.55 or 0.3) * (rec.isLocal and 1 or 0.6),
			jitter = 0.08,
		})
	end

	if rec.isLocal then
		local ratio = sat(speed / mountCfg.GallopSpeed)
		Feel.speed = speed
		Feel.speedRatio = ratio
		Feel.velocity = rec.vel
		Feel.grounded = grounded
		local gait = rec.anim.gait
		if gait ~= rec.gait then
			rec.gait = gait
			Feel.gait = gait
			Feel.GaitChanged:Fire(gait)
		end
	end
end

RunService:BindToRenderStep("SBRMountControl", Enum.RenderPriority.Input.Value + 1, function(dt)
	local rec = mounts[player]
	if rec and rec.control and rec.hum.Parent then
		control(rec, dt)
	end
end)

RunService:BindToRenderStep("SBRMountVisuals", Enum.RenderPriority.Camera.Value - 1, function(dt)
	for plr, rec in mounts do
		if rec.char.Parent and rec.hrp.Parent then
			updateMount(rec, dt)
		else
			destroyMount(plr)
		end
	end
end)

-- ---- players ----------------------------------------------------------------------------------------------
local function watch(plr: Player)
	plr.CharacterAdded:Connect(function(character)
		task.spawn(createMount, plr, character)
	end)
	plr.CharacterRemoving:Connect(function()
		destroyMount(plr)
		filterDirty = true
	end)
	if plr.Character then
		task.spawn(createMount, plr, plr.Character)
	end
end
Players.PlayerAdded:Connect(watch)
Players.PlayerRemoving:Connect(function(plr)
	destroyMount(plr)
	filterDirty = true
end)
for _, plr in Players:GetPlayers() do
	watch(plr)
end
