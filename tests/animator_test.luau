-- Simulates the animator moving through space and checks that planted hooves stay planted.
local HorseModel = require("../src/shared/HorseModel")
local Animator = require("../src/shared/HorseAnimator")
local Gait = require("../src/shared/Gait")

local failures = 0
local function check(cond, msg)
	if not cond then
		failures += 1
		print("FAIL: " .. msg)
	end
end

local LEGS = { "FL", "FR", "BL", "BR" }

local function simulate(speed, seconds, tweak)
	local rig = HorseModel.new({ outline = false })
	local steps, lands = 0, 0
	local anim = Animator.new(rig, {
		seed = 3,
		onStep = function()
			steps += 1
		end,
		onLand = function()
			lands += 1
		end,
	})
	local dt = 1 / 60
	local z = 0
	local prev = {}
	local maxSlide, maxSink, maxFloat = 0, 0, 0
	local frames = 0
	local nan = false
	local settle = 90 -- let the speed smoothing converge first
	for i = 1, settle + seconds * 60 do
		z -= speed * dt
		local input = { speed = speed, velocity = Vector3.new(0, 0, -speed), grounded = true, vy = 0 }
		if tweak then
			tweak(i, input, anim)
		end
		local adj = anim:update(dt, input)
		rig:step(CFrame.new(0, 0, z) * adj)
		if i > settle then
			local b = anim.lastBlend
			for _, leg in LEGS do
				local p = (anim.phase + b.offsets[leg]) % 1
				local pos = rig:hoofWorld(leg)
				if pos.X ~= pos.X or pos.Y ~= pos.Y then
					nan = true
				end
				-- skip the touchdown / lift-off frames: one frame advances the phase by up to ~0.06
				if p < b.stance - 0.1 and p > 0.1 and speed > 3 and prev[leg] then
					maxSlide = math.max(maxSlide, math.sqrt((pos.Z - prev[leg].Z) ^ 2 + (pos.X - prev[leg].X) ^ 2))
					maxFloat = math.max(maxFloat, pos.Y)
				end
				maxSink = math.min(maxSink, pos.Y)
				prev[leg] = pos
			end
			frames += 1
		end
	end
	return { slide = maxSlide, sink = maxSink, float = maxFloat, steps = steps, lands = lands, nan = nan, rig = rig, anim = anim }
end

for _, speed in { 0, 5, 14, 22, 32, 40 } do
	local r = simulate(speed, 4)
	print(("speed %2d  gait %-6s  planted-slide %.3f  float %.3f  sink %.3f  footfalls %d"):format(speed, r.anim.gait, r.slide, r.float, r.sink, r.steps))
	check(not r.nan, "NaN at speed " .. speed)
	check(r.sink > -0.25, ("hoof sinks into ground (%.2f) at speed %d"):format(r.sink, speed))
	if speed > 3 then
		check(r.slide < 0.02, ("planted hoof slides %.3f studs/frame at speed %d"):format(r.slide, speed))
		check(r.float < 0.3, ("planted hoof floats %.3f at speed %d"):format(r.float, speed))
		check(r.steps > 4, "no footfall events at speed " .. speed)
	else
		check(r.steps == 0, "footfalls while idle")
	end
end

-- emotes: rearing keeps the hind hooves on the ground; jumping tucks the legs then fires onLand
do
	local r = simulate(0, 4, function(i, _, anim)
		if i == 100 then
			anim:rear()
		end
	end)
	check(r.sink > -0.3, "rear: hooves sink " .. r.sink)
	local hind = r.rig:hoofWorld("BL")
	check(math.abs(hind.Y) < 0.5, "rear: hind hoof left the ground " .. hind.Y)
	print("rear ok, hind hoof y=" .. string.format("%.2f", hind.Y))
end
do
	local r = simulate(20, 3, function(i, input)
		if i > 130 and i < 160 then
			input.grounded = false
			input.vy = 30
		end
	end)
	check(r.lands == 1, "expected exactly one landing, got " .. r.lands)
	check(not r.nan, "NaN during jump")
	print("jump ok, landings=" .. r.lands)
end

if failures == 0 then
	print("animator tests passed")
else
	error(failures .. " failures")
end
