-- Run: python3 tests/run.py            (all tests)
--      python3 tests/run.py horse_model dump   (prints parts as JSON for the Blender preview)
local HorseModel = require("../src/shared/HorseModel")

local failures = 0
local function check(cond, msg)
	if not cond then
		failures += 1
		print("FAIL: " .. msg)
	end
end

local rig = HorseModel.new({ outline = true })
local S = HorseModel.Scale

local minY, maxY, minZ, maxZ, minX, maxX = math.huge, -math.huge, math.huge, -math.huge, math.huge, -math.huge
for _, entry in rig.parts do
	local p = entry.part
	local c, s = p.CFrame, p.Size
	for _, sx in { -1, 1 } do
		for _, sy in { -1, 1 } do
			for _, sz in { -1, 1 } do
				local w = c * Vector3.new(sx * s.X / 2, sy * s.Y / 2, sz * s.Z / 2)
				check(w.X == w.X and w.Y == w.Y and w.Z == w.Z, "NaN in " .. p.Name)
				minY, maxY = math.min(minY, w.Y), math.max(maxY, w.Y)
				minZ, maxZ = math.min(minZ, w.Z), math.max(maxZ, w.Z)
				minX, maxX = math.min(minX, w.X), math.max(maxX, w.X)
			end
		end
	end
end

local dumpMode = select(1, ...) == "dump"
if dumpMode then
	local out = {}
	for _, entry in rig.parts do
		local p = entry.part
		local c = p.CFrame
		local r = c.r
		local col = p.Color
		table.insert(
			out,
			string.format(
				'{"n":"%s","s":[%f,%f,%f],"p":[%f,%f,%f],"r":[%f,%f,%f,%f,%f,%f,%f,%f,%f],"c":[%f,%f,%f],"m":"%s"}',
				p.Name, p.Size.X, p.Size.Y, p.Size.Z, c.p.X, c.p.Y, c.p.Z,
				r[1][1], r[1][2], r[1][3], r[2][1], r[2][2], r[2][3], r[3][1], r[3][2], r[3][3],
				col.R, col.G, col.B, p.Material
			)
		)
	end
	print("[" .. table.concat(out, ",") .. "]")
	return
end

print(("parts: %d, bones: %d"):format(#rig.parts, #rig.order))
print(("bounds  x[%.2f, %.2f]  y[%.2f, %.2f]  z[%.2f, %.2f]  (studs)"):format(minX, maxX, minY, maxY, minZ, maxZ))

-- model sits on the ground, faces -Z, and is the expected size
check(math.abs(minY) < 0.05, "hooves should rest on y=0 (min y = " .. minY .. ")")
check(maxY > 6 and maxY < 9.5, "total height off: " .. maxY)
check(minZ < -4 and maxZ > 3, "length off")
check(maxX < 2.5 and minX > -2.5, "width off")
for leg, _ in HorseModel.Legs do
	local p = rig:hoofWorld(leg)
	check(math.abs(p.Y) < 0.05, "hoof " .. leg .. " not on the ground: " .. p.Y)
end

-- head is in front (-Z), tail behind (+Z)
local head = rig:boneWorld("Head").Position
local tail = rig:boneWorld("Tail1").Position
check(head.Z < tail.Z - 5, "head should be forward of tail")

-- 10k random pose steps never produce NaN / explode
for i = 1, 200 do
	for name, bone in rig.bones do
		bone.pose = CFrame.Angles(math.sin(i + #name) * 0.4, math.cos(i) * 0.2, math.sin(i * 0.3) * 0.2)
	end
	rig:step(CFrame.new(i, 0, -i))
end
local p = rig:boneWorld("Head").Position
check(p.X == p.X and math.abs(p.X) < 1e4, "pose explosion")

if failures == 0 then
	print("horse model tests passed")
else
	error(failures .. " failures")
end
