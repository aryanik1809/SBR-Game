-- Procedural animation for a HorseModel. Nothing here is keyframed: every pose comes from the gait
-- maths in Gait.luau plus a handful of springs, so it blends seamlessly between idle, walk, trot,
-- canter and gallop, banks into turns, tucks for jumps and reacts to braking.
--
-- Usage (every frame, after working out how the horse is moving):
--   local adjust = animator:update(dt, { speed = 31, yawRate = 0.4, grounded = true, vy = 0,
--                                        braking = 0, velocity = Vector3.new(...) })
--   rig:step(rootCFrame * adjust)
local Gait = require(script.Parent.Gait)
local HorseModel = require(script.Parent.HorseModel)

local Animator = {}
Animator.__index = Animator

local sat, smooth, damp, lerp = Gait.sat, Gait.smooth, Gait.damp, Gait.lerp
local TAU = math.pi * 2
local ANG = CFrame.Angles
local S = HorseModel.Scale

-- How far the body hangs below "legs fully straight" so the legs always have slack to reach the ground.
local DROP = 0.45
local CROUCH = 0.60 -- extra crouch at full speed
local LEGS = { "FL", "FR", "BL", "BR" }

export type Input = {
	speed: number,
	yawRate: number?,
	grounded: boolean?,
	vy: number?,
	braking: number?,
	velocity: Vector3?,
}

function Animator.new(rig, opts)
	opts = opts or {}
	local rng = Random.new(opts.seed or 7)
	local self = setmetatable({}, Animator)
	self.rig = rig
	self.rng = rng
	self.onStep = opts.onStep -- (leg, strength, worldPos)
	self.onLand = opts.onLand -- (strength)
	self.onEmote = opts.onEmote -- (name)
	self.time = rng:NextNumber() * 100
	self.phase = 0
	self.speed = 0
	self.yaw = 0
	self.airBlend = 0
	self.wasGrounded = true
	self.landDip = 0
	self.kick = 0
	self.lastP = { FL = 0, FR = 0, BL = 0, BR = 0 }
	self.rearT = nil
	self.tossT = nil
	self.pawT = nil
	self.idleTime = 0
	self.nextPaw = 6 + rng:NextNumber() * 6
	self.nextToss = 14 + rng:NextNumber() * 10
	self.earFlick = { L = 0, R = 0 }
	self.nextFlick = 2 + rng:NextNumber() * 3
	self.smoothRot = {} -- chain / scarf pendulum state
	self.bob = 0
	self.pitch = 0
	self.gait = "idle"
	return self
end

-- ---- emotes ------------------------------------------------------------------------------------
function Animator:rear()
	if not self.rearT and self.speed < 9 then
		self.rearT = 0
		if self.onEmote then
			self.onEmote("whinny")
		end
		return true
	end
	return false
end

function Animator:toss(kind: string?)
	if not self.tossT then
		self.tossT = 0
		if self.onEmote then
			self.onEmote(kind or "snort")
		end
	end
end

-- A short nose-up surge, used when a gallop starts.
function Animator:burst(amount: number?)
	self.kick = math.max(self.kick, amount or 1)
end

local REAR_LEN = 2.1
local function rearCurve(t: number): number
	return smooth(t / 0.55) * (1 - smooth((t - 1.35) / 0.75))
end

local TOSS_LEN = 0.9

-- Rotation that turns `restDir` onto `target` (both in the same parent frame).
local function rotFromTo(restDir: Vector3, target: Vector3): CFrame
	local d = math.clamp(restDir:Dot(target), -1, 1)
	local axis = restDir:Cross(target)
	if axis.Magnitude < 1e-5 then
		return CFrame.identity
	end
	return CFrame.fromAxisAngle(axis.Unit, math.acos(d))
end

local DOWN = Vector3.new(0, -1, 0)
local BACK = Vector3.new(0, 0, 1)

function Animator:_pendulum(bone: string, restDir: Vector3, worldTarget: Vector3, rate: number, dt: number, wobble: CFrame?)
	local parent = self.rig.bones[bone].parent
	local frame = parent and parent.world or CFrame.identity
	local local_ = frame:VectorToObjectSpace(worldTarget)
	local want = rotFromTo(restDir, local_.Unit)
	if wobble then
		want = want * wobble
	end
	local cur = self.smoothRot[bone] or want
	cur = cur:Lerp(want, 1 - math.exp(-rate * dt))
	self.smoothRot[bone] = cur
	self.rig:setPose(bone, cur)
end

function Animator:update(dt: number, input: Input): CFrame
	local rig = self.rig
	dt = math.min(dt, 1 / 20)
	self.time += dt
	local t = self.time

	-- smoothed motion state ---------------------------------------------------------------------
	self.speed = damp(self.speed, input.speed, input.speed > self.speed and 9 or 6, dt)
	if self.speed < 0.15 then
		self.speed = 0
	end
	local speed = self.speed
	self.yaw = damp(self.yaw, input.yawRate or 0, 7, dt)
	local speedRatio = sat(speed / 40)
	-- crouch lower as speed rises: the legs then reach farther fore and aft without overstretching
	local crouch = DROP + CROUCH * speedRatio
	local legLen = HorseModel.Legs.FL.upper + HorseModel.Legs.FL.lower
	local hEff = legLen - crouch + 0.12
	local blend = Gait.blend(speed, 0.93 * math.sqrt(math.max(0.01, legLen * legLen - hEff * hEff)))
	self.lastBlend = blend
	local moveBlend = smooth(speed / 3.5)
	local g, tr, w = blend.gallop, blend.trot, blend.walk
	if speed > 0 then
		self.phase = (self.phase + blend.freq * dt) % 1
	end
	local phase = self.phase
	self.gait = speed < 0.8 and "idle" or (g > 0.5 and "gallop" or (tr > 0.5 and "trot" or "walk"))
	if speed < 1.5 then
		self.idleTime += dt
	else
		self.idleTime = 0
	end

	-- airborne / landing --------------------------------------------------------------------------
	local grounded = input.grounded ~= false
	self.airBlend = damp(self.airBlend, grounded and 0 or 1, 14, dt)
	if grounded and not self.wasGrounded then
		local strength = sat(math.abs(input.vy or 0) / 45)
		self.landDip = -0.25 - 0.9 * strength
		if self.onLand then
			self.onLand(strength)
		end
	end
	self.wasGrounded = grounded
	self.landDip = damp(self.landDip, 0, 9, dt)
	self.kick = damp(self.kick, 0, 5, dt)

	-- emote timers ------------------------------------------------------------------------------------
	local rear = 0
	if self.rearT then
		self.rearT += dt
		rear = rearCurve(self.rearT)
		if self.rearT > REAR_LEN or speed > 12 then
			self.rearT = nil
			rear = 0
		end
	end
	local toss = 0
	if self.tossT then
		self.tossT += dt
		local u = self.tossT / TOSS_LEN
		toss = math.sin(math.pi * sat(u)) * (1 - 0.3 * u)
		if self.tossT > TOSS_LEN then
			self.tossT = nil
			toss = 0
		end
	end
	local paw = 0
	if speed < 1 and not self.rearT then
		if not self.pawT and self.idleTime > self.nextPaw then
			self.pawT = 0
			self.nextPaw = self.idleTime + 9 + self.rng:NextNumber() * 8
		end
		if not self.tossT and not self.pawT and self.idleTime > self.nextToss then
			self:toss(self.rng:NextNumber() < 0.5 and "snort" or "nicker")
			self.nextToss = self.idleTime + 18 + self.rng:NextNumber() * 14
		end
	end
	if self.pawT then
		if speed >= 1 then
			self.pawT = nil
		else
			self.pawT += dt
			paw = math.sin(math.pi * sat(self.pawT / 1.8))
			if self.pawT > 1.8 then
				self.pawT = nil
				paw = 0
			end
		end
	end

	-- body ---------------------------------------------------------------------------------------------
	local breathe = math.sin(t * 1.7) * 0.035
	local bob = (w * 0.09 * math.cos(2 * TAU * phase + 0.3) + tr * 0.20 * math.cos(2 * TAU * phase)
		+ g * 0.42 * math.cos(TAU * phase + 0.8)) * moveBlend
	bob = bob + breathe * (1 - moveBlend) + self.landDip + self.kick * 0.15
	local pitch = (g * 0.10 * math.sin(TAU * phase + 0.2) + tr * 0.03 * math.sin(2 * TAU * phase)
		+ w * 0.02 * math.sin(TAU * phase)) * moveBlend
	local vyPitch = math.clamp((input.vy or 0) * 0.012, -0.35, 0.35)
	local braking = sat(input.braking or 0)
	pitch = pitch + vyPitch * self.airBlend + braking * 0.16 + self.kick * 0.22
	local roll = math.clamp(self.yaw * 0.05 * (0.4 + speedRatio), -0.28, 0.28) + w * 0.02 * math.sin(TAU * phase) * moveBlend
	self.bob, self.pitch = bob, pitch
	rig:setPose("Body", CFrame.new(0, bob - crouch, 0) * ANG(pitch, 0, roll))

	-- legs -------------------------------------------------------------------------------------------------
	local bodyY = bob - crouch
	for _, name in LEGS do
		local L = HorseModel.Legs[name]
		local front = name:sub(1, 1) == "F"
		local p = (phase + blend.offsets[name]) % 1
		local shift = (front and 0.30 or -0.22) * blend.reach * g
		local f, h = Gait.footTarget(p, blend.stance, blend.reach, blend.lift, shift)
		f, h = f * moveBlend, h * moveBlend
		-- braking: fronts brace forward, hinds slide under
		f = f + braking * (front and 1.4 or 0.8)
		-- jump: tuck everything under / behind
		f = lerp(f, front and 1.9 or -1.7, self.airBlend)
		h = lerp(h, front and 1.8 or 1.7, self.airBlend)
		-- rearing: fronts curl up, hinds stay planted
		if front then
			f = lerp(f, 1.2, rear)
			h = lerp(h, 2.4, rear)
		end
		-- pawing with the front-left hoof
		if name == "FL" and paw > 0 then
			local s = (self.pawT or 0) * 5.5
			f = lerp(f, 1.1 - 1.3 * (s % 1), paw)
			h = lerp(h, 1.0 * math.max(0, 1 - (s % 1) * 2.0) + 0.1, paw)
		end
		-- Solve the leg in WORLD fore/aft + height, then rotate into the pitched body's frame so a
		-- planted hoof stays put even while the body rocks. (f, h) are relative to the rest hip.
		local sp, cp = math.sin(pitch), math.cos(pitch)
		local upOff = L.hipY - HorseModel.BodyPivotY -- hip height above the body pivot
		local hipU = HorseModel.BodyPivotY + bodyY + L.fwd * sp + upOff * cp
		local hipF = L.fwd * cp - upOff * sp - L.fwd -- how far pitch moved the hip forward
		local fw, uw = f - hipF, h - hipU
		local th1, rel = Gait.ik(L.upper, L.lower, fw * cp + uw * sp, -fw * sp + uw * cp, L.kneeSign)
		rig:setPose(name .. "_Up", ANG(th1, 0, 0))
		rig:setPose(name .. "_Lo", ANG(rel, 0, 0))

		-- footfall events ---------------------------------------------------------------------------------
		if moveBlend > 0.25 and grounded and p < self.lastP[name] - 0.5 and self.onStep then
			self.onStep(name, 0.25 + 0.75 * speedRatio, rig:hoofWorld(name))
		end
		self.lastP[name] = p
	end

	-- neck and head ----------------------------------------------------------------------------------------
	local look = (math.sin(t * 0.37) * 0.6 + math.sin(t * 0.91 + 1.3) * 0.4) * 0.30 * (1 - moveBlend)
	local nod = (w * 0.07 * math.sin(2 * TAU * phase + 0.5) + tr * 0.05 * math.sin(2 * TAU * phase)
		+ g * 0.16 * math.sin(TAU * phase + 1.0)) * moveBlend
	local neckPitch = 0.10 + 0.03 * math.sin(t * 1.7) - 0.34 * g - 0.10 * tr + nod
	neckPitch = neckPitch + 0.35 * rear + 0.35 * toss - 0.14 * braking - pitch * 0.45
	local neckYaw = math.clamp(self.yaw * 0.14, -0.45, 0.45) + look
	rig:setPose("Neck", ANG(neckPitch, neckYaw, -roll * 0.5))
	local headPitch = -neckPitch * 0.55 + 0.05 + 0.5 * toss * math.sin(self.time * 14) * 0.2 - 0.25 * toss + 0.10 * g
	rig:setPose("Head", ANG(headPitch, look * 0.5 + neckYaw * 0.3, 0.12 * toss * math.sin(t * 14)))

	-- ears -------------------------------------------------------------------------------------------------
	self.nextFlick -= dt
	if self.nextFlick <= 0 then
		self.earFlick[self.rng:NextNumber() < 0.5 and "L" or "R"] = 1
		self.nextFlick = 2 + self.rng:NextNumber() * 4
	end
	for _, side in { "L", "R" } do
		local sgn = side == "R" and 1 or -1
		self.earFlick[side] = damp(self.earFlick[side], 0, 7, dt)
		local flick = self.earFlick[side]
		local pin = 0.75 * g + 0.25 * tr + 0.45 * rear
		rig:setPose("Ear" .. side, ANG(pin + 0.35 * flick, 0, sgn * (0.12 + 0.35 * flick - 0.25 * g)))
	end

	-- tail ----------------------------------------------------------------------------------------------------
	local lift = -(0.30 * tr + 0.95 * g + 0.5 * rear) * moveBlend + (rear > 0 and -0.5 * rear or 0)
	local swish = math.sin(t * 1.15) * 0.28 * (1 - moveBlend) + math.sin(t * 2.3) * 0.08
	local lag = -self.yaw * 0.16
	for i, name in { "Tail1", "Tail2", "Tail3" } do
		local wave = math.sin(t * (3 + speedRatio * 5) - i * 0.9) * (0.06 + 0.16 * speedRatio + 0.05 * (1 - moveBlend))
		rig:setPose(name, ANG(lift * (i == 1 and 0.55 or 0.25) + bob * 0.08, swish * (i == 1 and 1 or 0.5) + lag + wave, 0))
	end

	-- mane ------------------------------------------------------------------------------------------------------
	local flutter = 0.05 + 0.20 * speedRatio
	for k, name in rig.maneBones do
		local side = name:sub(-1) == "R" and 1 or -1
		local a = math.sin(t * (7 + speed * 0.18) - k * 0.55) * flutter
		local c = math.sin(t * (5 + speed * 0.12) + k * 0.8) * flutter * 0.8
		rig:setPose(name, ANG(a + 0.22 * speedRatio - self.bob * 0.1 + neckPitch * 0.15, 0, side * (c + 0.08 * speedRatio)))
	end

	-- world-space things: chains swing, scarf streams in the wind ----------------------------------------------
	local vel = input.velocity or Vector3.new(0, 0, 0)
	local wind = (-vel * 0.12 + Vector3.new(0, -1, 0))
	for _, key in { "L", "R" } do
		for i, name in rig.chain[key] do
			local wob = ANG(math.sin(t * 9 + i) * 0.05 * speedRatio, 0, math.sin(t * 7 + i * 1.7) * 0.07 * speedRatio)
			self:_pendulum(name, DOWN, Vector3.new(0, -1, 0) + (-vel * 0.015), 14, dt, wob)
		end
	end
	if rig.bones.Scarf1 then
		for i = 1, 5 do
			local flut = ANG(math.sin(t * 14 - i * 1.1) * 0.22 * (0.2 + speedRatio), math.sin(t * 11 - i * 0.9) * 0.28 * (0.2 + speedRatio), 0)
			self:_pendulum("Scarf" .. i, BACK, wind, 9 + i, dt, flut)
		end
	end

	-- rider ---------------------------------------------------------------------------------------------------------
	if rig.bones.Rider then
		local lean = -(0.05 + 0.30 * g + 0.12 * tr + 0.45 * rear + 0.2 * self.kick) + 0.10 * braking - pitch * 0.6
		rig:setPose("Rider", CFrame.new(0, -bob * 0.25, 0))
		rig:setPose("RTorso", ANG(lean + math.sin(TAU * phase * 2) * 0.03 * moveBlend, -self.yaw * 0.06, -roll * 0.6))
		rig:setPose("RHead", ANG(-lean * 0.7 + 0.04 * math.sin(t * 2.1) + 0.12 * g, neckYaw * 0.5, roll * 0.3))
		rig:setPose("Hat", ANG(0.10 * speedRatio * 2 + math.sin(t * 13) * 0.05 * speedRatio + lean * -0.2, 0, math.sin(t * 9) * 0.04 * speedRatio))
		for _, key in { "L", "R" } do
			local sgn = key == "R" and 1 or -1
			local pull = nod * 0.8 + toss * 0.3
			rig:setPose("Arm" .. key .. "_Up", ANG(0.75 + 0.05 * math.sin(t * 6) * speedRatio, 0, sgn * 0.14))
			rig:setPose("Arm" .. key .. "_Lo", ANG(0.95 - pull - 0.5 * rear, 0, -sgn * 0.08))
			local knee = 1.0 + 0.14 * math.cos(TAU * phase + 0.8) * g + 0.2 * rear
			rig:setPose("Thigh" .. key, ANG(knee, 0, sgn * 0.66))
			rig:setPose("Shin" .. key, ANG(-1.2 - 0.1 * g, 0, -sgn * 0.30))
		end
	end

	-- rearing pivots the whole horse about its hind hooves ------------------------------------------------------------
	if rear > 0.001 then
		local pivot = Vector3.new(0, 0, 0.52 * S)
		return CFrame.new(pivot) * ANG(0.62 * rear, 0, 0) * CFrame.new(-pivot)
	end
	return CFrame.identity
end

return Animator
