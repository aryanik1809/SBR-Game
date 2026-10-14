-- Pure gait maths for the horse (no Roblox types, so it can be unit-tested with the plain Luau CLI).
-- Conventions: a leg hangs along -Y; a positive hip angle swings the foot FORWARD.
-- "forward" and "up" below are distances in the leg's sagittal plane, measured from the hip.
local Gait = {}

local function sat(x: number): number
	return math.clamp(x, 0, 1)
end

local function smooth(x: number): number
	x = sat(x)
	return x * x * (3 - 2 * x)
end

Gait.sat = sat
Gait.smooth = smooth

function Gait.lerp(a: number, b: number, t: number): number
	return a + (b - a) * t
end

-- Exponential smoothing that behaves the same at any frame rate.
function Gait.damp(current: number, target: number, rate: number, dt: number): number
	return target + (current - target) * math.exp(-rate * dt)
end

-- Distance covered by one full stride (studs). Longer strides at speed, like a real horse.
function Gait.strideLength(speed: number): number
	return 7 + 9 * sat((speed - 8) / 32)
end

-- Strides per second for a given ground speed.
function Gait.frequency(speed: number): number
	if speed < 0.5 then
		return 0
	end
	return speed / Gait.strideLength(speed)
end

-- How much walk / trot / gallop each contribute at a speed (sums to 1).
function Gait.weights(speed: number): (number, number, number)
	local gallop = smooth((speed - 27) / 10)
	local walk = math.min(1 - smooth((speed - 12) / 8), 1 - gallop)
	local trot = math.max(0, 1 - walk - gallop)
	return walk, trot, gallop
end

-- Footfall timing offsets (fraction of a stride) per leg: front-left, front-right, back-left, back-right.
Gait.Offsets = {
	walk = { FL = 0.25, FR = 0.75, BL = 0.0, BR = 0.5 }, -- four-beat lateral walk
	trot = { FL = 0.0, FR = 0.5, BL = 0.5, BR = 0.0 }, -- diagonal pairs
	gallop = { FL = 0.42, FR = 0.54, BL = 0.0, BR = 0.12 }, -- transverse gallop
}
-- Fraction of the stride a hoof spends on the ground.
Gait.Stance = { walk = 0.65, trot = 0.5, gallop = 0.36 }

export type Blend = {
	offsets: { [string]: number },
	stance: number,
	stride: number,
	freq: number,
	reach: number,
	lift: number,
	walk: number,
	trot: number,
	gallop: number,
}

-- Everything the animator needs for one speed. `reachCap` limits how far a planted hoof may travel
-- from its neutral spot (what the legs can physically reach); the stride shortens to fit.
function Gait.blend(speed: number, reachCap: number?): Blend
	local w, t, g = Gait.weights(speed)
	local offsets = {}
	for _, leg in { "FL", "FR", "BL", "BR" } do
		offsets[leg] = Gait.Offsets.walk[leg] * w + Gait.Offsets.trot[leg] * t + Gait.Offsets.gallop[leg] * g
	end
	local stance = Gait.Stance.walk * w + Gait.Stance.trot * t + Gait.Stance.gallop * g
	local stride = Gait.strideLength(speed)
	if reachCap then
		stride = math.min(stride, 2 * reachCap / stance)
	end
	return {
		offsets = offsets,
		stance = stance,
		stride = stride,
		freq = speed < 0.5 and 0 or speed / stride,
		-- half the distance the hoof travels backwards while planted
		reach = stride * stance / 2,
		-- how high the hoof clears the ground in the swing
		lift = 0.55 + 1.35 * t + 1.6 * g,
		walk = w,
		trot = t,
		gallop = g,
	}
end

-- Where a hoof should be at `phase` (0..1 of a stride). Returns (forward, height above ground).
function Gait.footTarget(phase: number, stance: number, reach: number, lift: number, shift: number): (number, number)
	if phase < stance then
		local t = phase / stance
		return shift + reach * (1 - 2 * t), 0
	end
	local t = (phase - stance) / (1 - stance)
	local e = t * t * (3 - 2 * t)
	return shift + reach * (-1 + 2 * e), lift * math.sin(math.pi * t)
end

-- Two-bone planar IK. The leg hangs straight down at angle 0 and a positive angle swings forward.
-- (tf, tu) = target relative to the hip (forward, up). kneeSign: +1 knee bends forward (front legs),
-- -1 the joint bends backward (hock of the hind legs).
-- Returns the upper-leg angle and the lower-leg angle RELATIVE to the upper leg.
function Gait.ik(L1: number, L2: number, tf: number, tu: number, kneeSign: number): (number, number)
	local d = math.sqrt(tf * tf + tu * tu)
	local maxD = (L1 + L2) * 0.999
	local minD = math.abs(L1 - L2) * 1.001 + 0.001
	local dc = math.clamp(d, minD, maxD)
	if d > 1e-6 then
		tf, tu = tf * dc / d, tu * dc / d
	else
		tf, tu = 0, -dc
	end
	d = dc
	local beta = math.atan2(tf, -tu)
	local cosg = (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d)
	local gamma = math.acos(math.clamp(cosg, -1, 1))
	local th1 = beta + kneeSign * gamma
	local kf, ku = L1 * math.sin(th1), -L1 * math.cos(th1)
	local th2 = math.atan2(tf - kf, -(tu - ku))
	return th1, th2 - th1
end

-- Forward kinematics (for tests): foot position for the angles IK returns.
function Gait.fk(L1: number, L2: number, th1: number, rel: number): (number, number)
	local th2 = th1 + rel
	return L1 * math.sin(th1) + L2 * math.sin(th2), -(L1 * math.cos(th1) + L2 * math.cos(th2))
end

return Gait
