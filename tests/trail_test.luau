local TrailMath = require("../src/shared/TrailMath")
local MapData = require("../src/shared/MapData")

local failures = 0
local function check(cond, msg)
	if not cond then
		failures += 1
		print("FAIL: " .. msg)
	end
end

local p = MapData.Trail.Points
for i = 1, #p do
	check(TrailMath.distance(p[i].X, p[i].Y) < 1e-6, "waypoint " .. i .. " should be on the trail")
	check(TrailMath.onTrail(p[i].X, p[i].Y), "waypoint " .. i .. " onTrail")
end
-- midpoint of a segment is on it, far away is not
local mx, mz = (p[1].X + p[2].X) / 2, (p[1].Y + p[2].Y) / 2
check(TrailMath.distance(mx, mz) < 1e-6, "segment midpoint")
check(not TrailMath.onTrail(mx + 100, mz), "100 studs off the trail")
check(math.abs(TrailMath.distance(mx + 7, mz) - 7) < 0.01 or TrailMath.distance(mx + 7, mz) <= 7.0001, "distance grows with offset")
-- beyond the ends the distance is to the endpoint
check(math.abs(TrailMath.distance(p[1].X, p[1].Y + 50) - 50) < 1e-6 or TrailMath.distance(p[1].X, p[1].Y + 50) < 50.01, "past the start")

if failures == 0 then
	print("trail tests passed")
else
	error(failures .. " failures")
end
