-- Run: luau tests/gait_test.luau   (plain Luau CLI, no Roblox needed)
local Gait = require("../src/shared/Gait")

local failures = 0
local function check(cond: boolean, msg: string)
	if not cond then
		failures += 1
		print("FAIL: " .. msg)
	end
end

-- IK reaches its target for both knee directions across the whole working envelope.
for _, sign in { 1, -1 } do
	for f = -3, 3, 0.5 do
		for h = 0, 2, 0.5 do
			local L1, L2 = 1.5, 1.8
			local tu = -(3.2 - h)
			local th1, rel = Gait.ik(L1, L2, f, tu, sign)
			local ff, fu = Gait.fk(L1, L2, th1, rel)
			local err = math.sqrt((ff - f) ^ 2 + (fu - tu) ^ 2)
			local reachable = math.sqrt(f * f + tu * tu) < (L1 + L2) * 0.999
			if reachable then
				check(err < 1e-6, ("ik error %.4f sign=%d f=%.1f h=%.1f"):format(err, sign, f, h))
			else
				-- unreachable targets must clamp to a fully extended leg pointing at the target
				check(math.abs(math.sqrt(ff * ff + fu * fu) - (L1 + L2) * 0.999) < 1e-6, "clamp length")
			end
			-- front knee must sit in front of the hip-foot line, hock behind it
			local kf = L1 * math.sin(th1)
			local lineAtKnee = f * (-L1 * math.cos(th1)) / tu
			if math.abs(f) > 0.1 or h > 0.1 then
				check((kf - lineAtKnee) * sign >= -1e-6, ("knee side wrong sign=%d f=%.1f h=%.1f"):format(sign, f, h))
			end
		end
	end
end

-- Gait weights always sum to 1 and move walk -> trot -> gallop as speed rises.
local prevGallop = 0
for s = 0, 60, 1 do
	local w, t, g = Gait.weights(s)
	check(math.abs(w + t + g - 1) < 1e-9, "weights sum at speed " .. s)
	check(w >= -1e-9 and t >= -1e-9 and g >= -1e-9, "negative weight at speed " .. s)
	check(g >= prevGallop - 1e-9, "gallop weight monotonic")
	prevGallop = g
end
local w0 = Gait.weights(4)
check(w0 > 0.99, "walk at low speed")
local _, _, g60 = Gait.weights(50)
check(g60 > 0.99, "gallop at high speed")

-- Foot target is continuous across the stance/swing boundary and loops at phase wrap.
for _, speed in { 6, 14, 22, 30, 42 } do
	local b = Gait.blend(speed)
	local f0, h0 = Gait.footTarget(0, b.stance, b.reach, b.lift, 0)
	local f1, h1 = Gait.footTarget(0.99999, b.stance, b.reach, b.lift, 0)
	check(math.abs(f0 - f1) < 0.05 and math.abs(h0 - h1) < 0.05, "wrap continuity at speed " .. speed)
	local fs, hs = Gait.footTarget(b.stance - 1e-6, b.stance, b.reach, b.lift, 0)
	local fe, he = Gait.footTarget(b.stance + 1e-6, b.stance, b.reach, b.lift, 0)
	check(math.abs(fs - fe) < 1e-3 and math.abs(hs - he) < 1e-3, "stance/swing continuity at speed " .. speed)
	check(b.freq > 0, "frequency positive at speed " .. speed)
	-- planted foot moves backwards at body speed: -2*reach / (stance / freq) == -speed
	local planted = 2 * b.reach / (b.stance / b.freq)
	check(math.abs(planted - speed) < 0.01 * speed, ("foot slides at speed %d (%.2f vs %.2f)"):format(speed, planted, speed))
end

if failures == 0 then
	print("gait tests passed")
else
	print(failures .. " failures")
	error("gait tests failed")
end
