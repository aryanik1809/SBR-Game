-- Minimal stand-ins for the Roblox types the pure modules use, so they can run under the plain
-- Luau CLI via `python3 tests/run.py`. Only what HorseModel / HorseAnimator touch is implemented.

local V3 = {}
local V3methods = {}
local V3mt = {}

local function v3(x, y, z)
	return setmetatable({ X = x or 0, Y = y or 0, Z = z or 0 }, V3mt)
end

function V3methods.Dot(a, b)
	return a.X * b.X + a.Y * b.Y + a.Z * b.Z
end
function V3methods.Cross(a, b)
	return v3(a.Y * b.Z - a.Z * b.Y, a.Z * b.X - a.X * b.Z, a.X * b.Y - a.Y * b.X)
end
function V3methods.Lerp(a, b, t)
	return v3(a.X + (b.X - a.X) * t, a.Y + (b.Y - a.Y) * t, a.Z + (b.Z - a.Z) * t)
end
V3mt.__index = function(t, k)
	if k == "Magnitude" then
		return math.sqrt(t.X * t.X + t.Y * t.Y + t.Z * t.Z)
	elseif k == "Unit" then
		local m = math.sqrt(t.X * t.X + t.Y * t.Y + t.Z * t.Z)
		if m == 0 then
			return v3(0, 0, 0)
		end
		return v3(t.X / m, t.Y / m, t.Z / m)
	end
	return V3methods[k]
end
V3mt.__add = function(a, b)
	return v3(a.X + b.X, a.Y + b.Y, a.Z + b.Z)
end
V3mt.__sub = function(a, b)
	return v3(a.X - b.X, a.Y - b.Y, a.Z - b.Z)
end
V3mt.__mul = function(a, b)
	if type(a) == "number" then
		return v3(a * b.X, a * b.Y, a * b.Z)
	elseif type(b) == "number" then
		return v3(a.X * b, a.Y * b, a.Z * b)
	end
	return v3(a.X * b.X, a.Y * b.Y, a.Z * b.Z)
end
V3mt.__div = function(a, b)
	return v3(a.X / b, a.Y / b, a.Z / b)
end
V3mt.__unm = function(a)
	return v3(-a.X, -a.Y, -a.Z)
end
V3mt.__eq = function(a, b)
	return a.X == b.X and a.Y == b.Y and a.Z == b.Z
end
V3.new = v3
V3.zero = v3(0, 0, 0)
V3.one = v3(1, 1, 1)
V3.xAxis = v3(1, 0, 0)
V3.yAxis = v3(0, 1, 0)
V3.zAxis = v3(0, 0, 1)

-- CFrame: p = position, r = 3x3 rotation (r[row][col]); columns are right / up / back.
local CF = {}
local CFmethods = {}
local CFmt = {}

local function cf(p, r)
	return setmetatable({ p = p, r = r }, CFmt)
end
local IDENT = { { 1, 0, 0 }, { 0, 1, 0 }, { 0, 0, 1 } }

local function matmul(a, b)
	local out = { {}, {}, {} }
	for i = 1, 3 do
		for j = 1, 3 do
			out[i][j] = a[i][1] * b[1][j] + a[i][2] * b[2][j] + a[i][3] * b[3][j]
		end
	end
	return out
end
local function rotv(r, v)
	return v3(
		r[1][1] * v.X + r[1][2] * v.Y + r[1][3] * v.Z,
		r[2][1] * v.X + r[2][2] * v.Y + r[2][3] * v.Z,
		r[3][1] * v.X + r[3][2] * v.Y + r[3][3] * v.Z
	)
end
local function transpose(r)
	return { { r[1][1], r[2][1], r[3][1] }, { r[1][2], r[2][2], r[3][2] }, { r[1][3], r[2][3], r[3][3] } }
end

CFmt.__index = function(t, k)
	if k == "Position" then
		return t.p
	elseif k == "RightVector" then
		return v3(t.r[1][1], t.r[2][1], t.r[3][1])
	elseif k == "UpVector" then
		return v3(t.r[1][2], t.r[2][2], t.r[3][2])
	elseif k == "LookVector" then
		return v3(-t.r[1][3], -t.r[2][3], -t.r[3][3])
	end
	return CFmethods[k]
end
CFmt.__mul = function(a, b)
	if getmetatable(b) == V3mt then
		return a.p + rotv(a.r, b)
	end
	return cf(a.p + rotv(a.r, b.p), matmul(a.r, b.r))
end
CFmt.__add = function(a, b)
	return cf(a.p + b, a.r)
end
CFmt.__sub = function(a, b)
	return cf(a.p - b, a.r)
end
function CFmethods.Inverse(a)
	local rt = transpose(a.r)
	return cf(-rotv(rt, a.p), rt)
end
function CFmethods.PointToWorldSpace(a, v)
	return a * v
end
function CFmethods.VectorToWorldSpace(a, v)
	return rotv(a.r, v)
end
function CFmethods.VectorToObjectSpace(a, v)
	return rotv(transpose(a.r), v)
end
function CFmethods.PointToObjectSpace(a, v)
	return a:Inverse() * v
end
function CFmethods.ToObjectSpace(a, b)
	return a:Inverse() * b
end
function CFmethods.Lerp(a, b, t)
	return cf(a.p:Lerp(b.p, t), t < 0.5 and a.r or b.r)
end
function CFmethods.GetComponents(a)
	local r = a.r
	return a.p.X, a.p.Y, a.p.Z, r[1][1], r[1][2], r[1][3], r[2][1], r[2][2], r[2][3], r[3][1], r[3][2], r[3][3]
end

CF.identity = cf(v3(0, 0, 0), IDENT)
CF.new = function(x, y, z)
	if type(x) == "table" then
		return cf(x, IDENT)
	end
	return cf(v3(x or 0, y or 0, z or 0), IDENT)
end
CF.Angles = function(rx, ry, rz)
	local cx, sx = math.cos(rx), math.sin(rx)
	local cy, sy = math.cos(ry), math.sin(ry)
	local cz, sz = math.cos(rz), math.sin(rz)
	local Rx = { { 1, 0, 0 }, { 0, cx, -sx }, { 0, sx, cx } }
	local Ry = { { cy, 0, sy }, { 0, 1, 0 }, { -sy, 0, cy } }
	local Rz = { { cz, -sz, 0 }, { sz, cz, 0 }, { 0, 0, 1 } }
	return cf(v3(0, 0, 0), matmul(Rx, matmul(Ry, Rz)))
end
CF.fromMatrix = function(pos, vx, vy, vz)
	vz = vz or vx:Cross(vy)
	return cf(pos, { { vx.X, vy.X, vz.X }, { vx.Y, vy.Y, vz.Y }, { vx.Z, vy.Z, vz.Z } })
end
CF.lookAt = function(at, target, up)
	up = up or V3.yAxis
	local look = (target - at).Unit
	local right = look:Cross(up).Unit
	if right.Magnitude < 1e-6 then
		right = V3.xAxis
	end
	local upv = right:Cross(look)
	local back = -look
	return CF.fromMatrix(at, right, upv, back)
end
CF.fromAxisAngle = function(axis, angle)
	local a = axis.Unit
	local c, s = math.cos(angle), math.sin(angle)
	local t = 1 - c
	local x, y, z = a.X, a.Y, a.Z
	return cf(v3(0, 0, 0), {
		{ t * x * x + c, t * x * y - s * z, t * x * z + s * y },
		{ t * x * y + s * z, t * y * y + c, t * y * z - s * x },
		{ t * x * z - s * y, t * y * z + s * x, t * z * z + c },
	})
end

-- Enum proxy: Enum.Material.Metal -> "Material.Metal"
local Enum = setmetatable({}, {
	__index = function(_, group)
		return setmetatable({}, {
			__index = function(_, item)
				return group .. "." .. item
			end,
		})
	end,
})

-- Instance stub that records properties and children.
local Instance = {}
local instMethods = {}
local instMt = {}
instMt.__index = function(t, k)
	local props = rawget(t, "_props")
	if props[k] ~= nil then
		return props[k]
	end
	return instMethods[k]
end
instMt.__newindex = function(t, k, v)
	local props = rawget(t, "_props")
	if k == "Parent" then
		local old = props.Parent
		if old then
			local ch = rawget(old, "_children")
			local i = table.find(ch, t)
			if i then
				table.remove(ch, i)
			end
		end
		if v then
			table.insert(rawget(v, "_children"), t)
		end
	end
	props[k] = v
end
function instMethods.GetChildren(t)
	return table.clone(rawget(t, "_children"))
end
function instMethods.Destroy(t)
	t.Parent = nil
end
function instMethods.FindFirstChild(t, name)
	for _, c in rawget(t, "_children") do
		if c.Name == name then
			return c
		end
	end
	return nil
end
Instance.new = function(class)
	return setmetatable({ _props = { ClassName = class, Name = class }, _children = {} }, instMt)
end

local workspace = Instance.new("Workspace")
instMethods.IsDescendantOf = function(t, ancestor)
	local p = t.Parent
	while p do
		if p == ancestor then
			return true
		end
		p = p.Parent
	end
	return false
end
instMethods.BulkMoveTo = function(_, parts, cfs, _mode)
	for i, p in parts do
		p.CFrame = cfs[i]
	end
end

local Random = {}
Random.new = function(seed)
	math.randomseed(seed or 1)
	local r = {}
	function r.NextNumber(_, a, b)
		if a then
			return a + math.random() * (b - a)
		end
		return math.random()
	end
	return r
end

local Color3 = {
	fromRGB = function(r, g, b)
		return { R = r / 255, G = g / 255, B = b / 255 }
	end,
	new = function(r, g, b)
		return { R = r, G = g, B = b }
	end,
}

-- tests/run.py injects these as locals ahead of every module it loads.
return {
	Vector3 = V3,
	CFrame = CF,
	Color3 = Color3,
	Enum = Enum,
	Instance = Instance,
	workspace = workspace,
	Random = Random,
}
