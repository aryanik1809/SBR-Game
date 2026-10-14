-- Dumps the rig in a given animation state as JSON for tests/render_dump.py.
--   python3 tests/run.py posedump dump gallop > rig.json     (gallop | walk | trot | rear | jump | idle)
local HorseModel = require("../src/shared/HorseModel")
local Animator = require("../src/shared/HorseAnimator")

local mode, pose = ...
if mode ~= "dump" then
	print("posedump: nothing to check (use `dump <pose>`)")
	return
end

local speeds = { gallop = 40, trot = 22, walk = 10, rear = 0, jump = 24, idle = 0, brake = 30 }
local speed = speeds[pose] or 0
local rig = HorseModel.new({ outline = false })
local anim = Animator.new(rig, { seed = 3 })
local dt = 1 / 60
local z = 0
local frames = 200
for i = 1, frames do
	z -= speed * dt
	local input = { speed = speed, velocity = Vector3.new(0, 0, -speed), grounded = true, vy = 0 }
	local y = 0
	if pose == "rear" and i == 120 then
		anim:rear()
	end
	if pose == "jump" and i > 150 then
		input.grounded = false
		input.vy = 6
		y = 2.2
	end
	if pose == "brake" and i > 150 then
		input.speed = 4
		input.braking = 1
	end
	local adj = anim:update(dt, input)
	rig:step(CFrame.new(0, y, z) * adj)
	if pose == "rear" and i == 120 + 45 then
		break
	end
end

local out = {}
local function add(p)
	local c = p.CFrame
	local r = c.r
	local col = p.Color
	table.insert(
		out,
		string.format(
			'{"n":"%s","s":[%f,%f,%f],"p":[%f,%f,%f],"r":[%f,%f,%f,%f,%f,%f,%f,%f,%f],"c":[%f,%f,%f],"m":"%s"}',
			p.Name, p.Size.X, p.Size.Y, p.Size.Z, c.p.X, c.p.Y, c.p.Z - z,
			r[1][1], r[1][2], r[1][3], r[2][1], r[2][2], r[2][3], r[3][1], r[3][2], r[3][3],
			col.R, col.G, col.B, p.Material
		)
	)
end
for _, entry in rig.parts do
	add(entry.part)
end
for _, rein in rig.reins do
	for _, p in rein.parts do
		add(p)
	end
end
print("[" .. table.concat(out, ",") .. "]")
