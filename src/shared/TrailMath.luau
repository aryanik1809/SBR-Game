-- Where is a point relative to the race trail? (Read-only helper; the trail itself is built by the server.)
local MapData = require(script.Parent.MapData)

local TrailMath = {}

-- Distance in studs from (x, z) to the trail centre line.
function TrailMath.distance(x: number, z: number): number
	local best = math.huge
	local points = MapData.Trail.Points
	for i = 1, #points - 1 do
		local ax, az = points[i].X, points[i].Y
		local bx, bz = points[i + 1].X, points[i + 1].Y
		local abx, abz = bx - ax, bz - az
		local len2 = abx * abx + abz * abz
		local t = 0
		if len2 > 0 then
			t = math.clamp(((x - ax) * abx + (z - az) * abz) / len2, 0, 1)
		end
		local dx, dz = x - (ax + abx * t), z - (az + abz * t)
		best = math.min(best, math.sqrt(dx * dx + dz * dz))
	end
	return best
end

-- True if the point is on the packed-dirt trail (not just near it).
function TrailMath.onTrail(x: number, z: number): boolean
	return TrailMath.distance(x, z) <= MapData.Trail.Width / 2 - 1
end

return TrailMath
