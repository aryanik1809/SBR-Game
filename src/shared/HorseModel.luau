-- Builds the saddled horse and its rider out of Parts (no uploaded meshes needed) and owns the
-- skeleton that animates them. Proportions follow the Blender model in assets/horse.
--
-- Skeleton: a tree of "bones". Each bone has a rest pivot; every frame
--   world = parent.world * CFrame.new(offset) * pose
-- and each part is placed at bone.world * rel. The animator only writes `pose`.
--
-- Local frame of the model: forward = -Z, up = +Y, right = +X, origin on the ground under the horse.
local HorseModel = {}
HorseModel.__index = HorseModel

local S = 3.4 -- studs per metre of the Blender model (horse is ~6.5 studs tall)
HorseModel.Scale = S
-- Multiplies every part colour (set before HorseModel.new). The world lighting is bright, so Config.Mount.ColorScale
-- lets you darken or lighten the whole horse and rider in one place.
HorseModel.ColorScale = 1

-- Leg geometry in studs, shared with the animator. `fwd` = how far the hip is in front of the body pivot.
HorseModel.Legs = {
	FL = { x = 0.165, y = 0.52, hipY = 0.90 * S, upper = 0.38 * S, lower = 0.52 * S, kneeSign = 1 },
	FR = { x = -0.165, y = 0.52, hipY = 0.90 * S, upper = 0.38 * S, lower = 0.52 * S, kneeSign = 1 },
	BL = { x = 0.20, y = -0.52, hipY = 0.90 * S, upper = 0.40 * S, lower = 0.50 * S, kneeSign = -1 },
	BR = { x = -0.20, y = -0.52, hipY = 0.90 * S, upper = 0.40 * S, lower = 0.50 * S, kneeSign = -1 },
}
for _, leg in HorseModel.Legs do
	leg.fwd = leg.y * S
end
HorseModel.BodyPivotY = 0.92 * S

local HIDE = Color3.fromRGB(150, 88, 42)
local HIDE_LT = Color3.fromRGB(178, 110, 54)
local HIDE_DK = Color3.fromRGB(108, 62, 30)
local MUZZLE = Color3.fromRGB(168, 172, 182)
local MUZZLE_LT = Color3.fromRGB(196, 200, 208)
local SOCK = Color3.fromRGB(142, 146, 156)
local HOOF = Color3.fromRGB(66, 64, 74)
local MANE = Color3.fromRGB(38, 29, 25)
local MANE_LT = Color3.fromRGB(72, 54, 44)
local RED = Color3.fromRGB(178, 28, 34)
local CREAM = Color3.fromRGB(238, 222, 190)
local LEATHER = Color3.fromRGB(158, 82, 28)
local LEATHER_DK = Color3.fromRGB(92, 56, 34)
local SADDLE = Color3.fromRGB(176, 98, 38)
local GOLD = Color3.fromRGB(246, 190, 40)
local EYE_W = Color3.fromRGB(246, 243, 232)
local EYE_B = Color3.fromRGB(16, 12, 12)
local SKIN = Color3.fromRGB(236, 190, 150)
local JACKET = Color3.fromRGB(30, 118, 142)
local JACKET_DK = Color3.fromRGB(20, 80, 104)
local PANTS = Color3.fromRGB(228, 220, 200)
local BOOT = Color3.fromRGB(86, 54, 34)
local HAT = Color3.fromRGB(226, 208, 170)
local HAT_BAND = Color3.fromRGB(58, 38, 30)

local PLASTIC = Enum.Material.SmoothPlastic
local FABRIC = Enum.Material.Fabric
local METAL = Enum.Material.Metal

-- Blender (x right, y forward, z up, metres) -> model space (x right, y up, -z forward, studs).
local function B(v: Vector3): Vector3
	return Vector3.new(v.X, v.Z, -v.Y) * S
end
-- Same mapping for pure directions (no scale).
local function D(v: Vector3): Vector3
	return Vector3.new(v.X, v.Z, -v.Y)
end
local function V(x: number, y: number, z: number): Vector3
	return Vector3.new(x, y, z)
end

local Builder = {}
Builder.__index = Builder

local function addBone(self, name: string, parent: string?, restB: Vector3)
	local rest = B(restB)
	local p = parent and self.bones[parent] or nil
	local bone = {
		name = name,
		parent = p,
		rest = rest,
		offset = rest - (p and p.rest or Vector3.zero),
		pose = CFrame.identity,
		world = CFrame.new(rest),
	}
	self.bones[name] = bone
	table.insert(self.order, bone)
	return bone
end

local function mk(self, boneName: string, restCF: CFrame, size: Vector3, color: Color3, material: Enum.Material)
	local part = Instance.new("Part")
	part.Name = boneName
	part.Size = size
	local k = HorseModel.ColorScale
	part.Color = k == 1 and color or Color3.new(math.min(1, color.R * k), math.min(1, color.G * k), math.min(1, color.B * k))
	part.Material = material
	part.Anchored = true
	part.CanCollide = false
	part.CanQuery = false
	part.CanTouch = false
	part.CastShadow = false
	part.TopSurface = Enum.SurfaceType.Smooth
	part.BottomSurface = Enum.SurfaceType.Smooth
	part.CFrame = restCF
	part.Parent = self.model
	local bone = self.bones[boneName]
	table.insert(self.parts, { part = part, bone = bone, rel = CFrame.new(-bone.rest) * restCF })
	return part
end

-- Axis-aligned box. `c` centre and `s` = (width, length, height) in Blender metres.
local function block(self, bone: string, c: Vector3, s: Vector3, color: Color3, material: Enum.Material?, rot: CFrame?)
	local cf = CFrame.new(B(c)) * (rot or CFrame.identity)
	return mk(self, bone, cf, Vector3.new(s.X * S, s.Z * S, s.Y * S), color, material or PLASTIC)
end

-- Box stretched between two points. Local Y runs p0 -> p1; `wide` is the size along the part's X,
-- `thick` along its Z. `ref` picks which way X points (default: model X).
local function seg(self, bone: string, p0: Vector3, p1: Vector3, wide: number, thick: number, color: Color3, material: Enum.Material?, ref: Vector3?)
	local a, b = B(p0), B(p1)
	local d = b - a
	local len = d.Magnitude
	local y = d.Unit
	local r = ref and D(ref).Unit or Vector3.xAxis
	if math.abs(y:Dot(r)) > 0.95 then
		r = Vector3.zAxis
	end
	local x = (r - y * y:Dot(r)).Unit
	local cf = CFrame.fromMatrix((a + b) / 2, x, y, x:Cross(y))
	return mk(self, bone, cf, Vector3.new(wide * S, len, thick * S), color, material or PLASTIC)
end

-- Box with its own orientation given by two Blender-space axis directions.
local function framed(self, bone: string, c: Vector3, ax: Vector3, ay: Vector3, size: Vector3, color: Color3, material: Enum.Material?)
	-- orthonormalise so callers can pass any two non-parallel directions
	local x = D(ax).Unit
	local y = D(ay)
	y = (y - x * x:Dot(y)).Unit
	local cf = CFrame.fromMatrix(B(c), x, y)
	return mk(self, bone, cf, size * S, color, material or PLASTIC)
end

-- Box whose silhouette has chamfered corners (a "cross" of two boxes), lighter on top, darker below.
local function chamfered(self, bone: string, c: Vector3, s: Vector3, k: number, top: Color3, mid: Color3, bottom: Color3)
	block(self, bone, c, V(s.X, s.Y, s.Z - 2 * k), mid)
	block(self, bone, c + V(0, 0, s.Z / 2 - k / 2), V(s.X - 2 * k, s.Y, k), top)
	block(self, bone, c - V(0, 0, s.Z / 2 - k / 2), V(s.X - 2 * k, s.Y, k), bottom)
end

-- Small square gold ring (4 bars) in the plane spanned by a and b.
local function goldRing(self, bone: string, c: Vector3, a: Vector3, b: Vector3, size: number, bar: number)
	local half = size / 2 - bar / 2
	for _, sgn in { -1, 1 } do
		framed(self, bone, c + b * (sgn * half), a, b, V(size, bar, bar), GOLD, METAL)
		framed(self, bone, c + a * (sgn * half), a, b, V(bar, size, bar), GOLD, METAL)
	end
end

local function buckle(self, bone: string, c: Vector3, a: Vector3, b: Vector3, w: number, h: number)
	local bar = math.max(0.012, math.min(w, h) * 0.22)
	for _, sgn in { -1, 1 } do
		framed(self, bone, c + b * (sgn * (h / 2 - bar / 2)), a, b, V(w, bar, 0.012), GOLD, METAL)
		framed(self, bone, c + a * (sgn * (w / 2 - bar / 2)), a, b, V(bar, h, 0.012), GOLD, METAL)
	end
	framed(self, bone, c, a, b, V(bar * 0.6, h * 0.8, 0.016), GOLD, METAL)
end

-- Head geometry (Blender metres). Parameter t runs 0 (skull) .. 1 (end of the nose bridge).
local HEAD_C0 = V(0.0, 0.97, 1.60)
local HEAD_F = V(0.0, 0.82, -0.57).Unit
local HEAD_U = V(1, 0, 0)
local HEAD_V = HEAD_U:Cross(HEAD_F) -- "up" perpendicular to the head axis
local function headW(t: number): number
	return 0.40 - 0.09 * t
end
local function headH(t: number): number
	return 0.46 - 0.11 * t
end
local function headPt(t: number, side: number, up: number, out: number?): Vector3
	return HEAD_C0 + HEAD_F * (0.5 * t) + HEAD_U * (side * (headW(t) / 2 + (out or 0))) + HEAD_V * (up * headH(t) / 2)
end

local function buildHorse(self, rng: Random)
	-- ---- skeleton ------------------------------------------------------------------------
	addBone(self, "Root", nil, V(0, 0, 0))
	addBone(self, "Body", "Root", V(0, 0, 0.92))
	addBone(self, "Neck", "Body", V(0, 0.58, 0.98))
	addBone(self, "Head", "Neck", V(0, 0.95, 1.46))
	local earBase = {}
	for _, side in { -1, 1 } do
		earBase[side] = headPt(0, side * 0.55, 1.0)
		addBone(self, side == 1 and "EarR" or "EarL", "Head", earBase[side])
	end
	addBone(self, "Tail1", "Body", V(0, -0.82, 1.0))
	local tailDir = V(0, -0.55, -0.83).Unit
	local tailP1 = V(0, -0.82, 1.0)
	local tailP2 = tailP1 + tailDir * 0.30
	local tailP3 = tailP2 + tailDir * 0.28
	addBone(self, "Tail2", "Tail1", tailP2)
	addBone(self, "Tail3", "Tail2", tailP3)
	for name, leg in HorseModel.Legs do
		local top = V(leg.x, leg.y, leg.hipY / S)
		addBone(self, name .. "_Up", "Body", top)
		addBone(self, name .. "_Lo", name .. "_Up", top - V(0, 0, leg.upper / S))
	end

	-- ---- torso ---------------------------------------------------------------------------
	chamfered(self, "Body", V(0, -0.55, 0.95), V(0.62, 0.50, 0.70), 0.07, HIDE_LT, HIDE, HIDE_DK)
	chamfered(self, "Body", V(0, -0.02, 0.89), V(0.60, 0.64, 0.72), 0.07, HIDE_LT, HIDE, HIDE_DK)
	chamfered(self, "Body", V(0, 0.56, 0.93), V(0.58, 0.52, 0.72), 0.07, HIDE_LT, HIDE, HIDE_DK)

	-- ---- saddle gear ---------------------------------------------------------------------
	local topZ = 0.89 + 0.36 -- back of the barrel
	-- blanket: red cloth with cream trim and a gold pinstripe
	block(self, "Body", V(0, 0, topZ + 0.012), V(0.60, 0.58, 0.026), RED, FABRIC)
	for _, side in { -1, 1 } do
		block(self, "Body", V(side * 0.309, 0, 1.10), V(0.026, 0.52, 0.30), RED, FABRIC)
		block(self, "Body", V(side * 0.313, 0, 0.945), V(0.032, 0.54, 0.034), CREAM, FABRIC)
		block(self, "Body", V(side * 0.236, 0, topZ + 0.020), V(0.014, 0.58, 0.014), GOLD, FABRIC)
	end
	for _, dy in { -1, 1 } do
		block(self, "Body", V(0, dy * 0.296, topZ + 0.012), V(0.62, 0.034, 0.030), CREAM, FABRIC)
		block(self, "Body", V(0, dy * 0.262, topZ + 0.020), V(0.50, 0.012, 0.012), GOLD, FABRIC)
	end
	-- saddle seat, skirts, cantle, pommel
	local seatZ = topZ + 0.026
	block(self, "Body", V(0, -0.02, seatZ + 0.014), V(0.40, 0.34, 0.034), SADDLE, FABRIC)
	for _, side in { -1, 1 } do
		block(self, "Body", V(side * 0.332, -0.02, 1.12), V(0.032, 0.32, 0.24), SADDLE, FABRIC)
		block(self, "Body", V(side * 0.349, -0.02, 1.12), V(0.010, 0.27, 0.19), LEATHER_DK, FABRIC)
		block(self, "Body", V(side * 0.12, -0.02, seatZ + 0.034), V(0.025, 0.30, 0.012), CREAM, FABRIC) -- stitching
	end
	block(self, "Body", V(0, -0.02, seatZ + 0.045), V(0.24, 0.26, 0.030), LEATHER_DK, FABRIC)
	block(self, "Body", V(0, -0.17, seatZ + 0.080), V(0.32, 0.055, 0.115), SADDLE, FABRIC, CFrame.Angles(0.25, 0, 0))
	block(self, "Body", V(0, 0.115, seatZ + 0.070), V(0.17, 0.060, 0.095), SADDLE, FABRIC, CFrame.Angles(-0.2, 0, 0))
	block(self, "Body", V(0, 0.125, seatZ + 0.145), V(0.060, 0.055, 0.060), LEATHER, FABRIC)
	-- girth strap, breast collar, billets
	block(self, "Body", V(0, 0.19, topZ + 0.034), V(0.64, 0.050, 0.020), LEATHER, FABRIC)
	block(self, "Body", V(0, 0.66, 1.296), V(0.58, 0.046, 0.018), LEATHER, FABRIC)
	for _, side in { -1, 1 } do
		block(self, "Body", V(side * 0.316, 0.19, 1.10), V(0.030, 0.05, 0.31), LEATHER, FABRIC)
		block(self, "Body", V(side * 0.296, 0.66, 1.07), V(0.030, 0.046, 0.40), LEATHER, FABRIC)
		for _, y in { -0.045, 0.05 } do
			block(self, "Body", V(side * 0.349, y, 0.86), V(0.020, 0.036, 0.26), LEATHER, FABRIC)
		end
		buckle(self, "Body", V(side * 0.334, 0.19, 0.86), V(0, 1, 0), V(0, 0, 1), 0.052, 0.07)
		buckle(self, "Body", V(side * 0.36, 0.05, 0.80), V(0, 1, 0), V(0, 0, 1), 0.05, 0.06)
	end
	block(self, "Body", V(0, 0.835, 0.96), V(0.05, 0.016, 0.50), LEATHER, FABRIC)
	buckle(self, "Body", V(0, 0.848, 0.84), V(1, 0, 0), V(0, 0, 1), 0.085, 0.065)
	-- saddlebags: tan on the right, dark on the left
	for _, side in { -1, 1 } do
		local mat = side == 1 and LEATHER or LEATHER_DK
		local x = side * 0.40
		block(self, "Body", V(x, -0.17, 1.10), V(0.095, 0.15, 0.13), mat, FABRIC)
		block(self, "Body", V(x + side * 0.002, -0.17, 1.178), V(0.105, 0.162, 0.034), mat, FABRIC)
		buckle(self, "Body", V(x + side * 0.052, -0.17, 1.13), V(0, 1, 0), V(0, 0, 1), 0.034, 0.05)
		block(self, "Body", V(side * 0.355, -0.17, 1.12), V(0.060, 0.03, 0.020), LEATHER, FABRIC)
	end

	-- ---- neck, mane ------------------------------------------------------------------------
	local neckA, neckB = V(0, 0.52, 0.92), V(0, 0.95, 1.46)
	seg(self, "Neck", neckA, neckB, 0.40, 0.44, HIDE)
	seg(self, "Neck", neckA + V(0, -0.02, 0.0), neckB + V(0, -0.02, 0.02), 0.34, 0.50, HIDE_LT)
	-- chest/neck underside darker
	seg(self, "Neck", neckA + V(0, 0.0, -0.1), neckB + V(0, 0.04, -0.1), 0.30, 0.46, HIDE_DK)
	local crest0, crest1 = V(0, 0.42, 1.20), V(0, 0.84, 1.66)
	local maneBones = {}
	for i = 0, 8 do
		local t = i / 8
		for _, side in { -1, 1 } do
			local name = ("Mane%d%s"):format(i, side == 1 and "R" or "L")
			local pivot = crest0:Lerp(crest1, t) + V(side * 0.035, -0.02, 0.0)
			addBone(self, name, "Neck", pivot)
			local d = V(side * (0.55 + rng:NextNumber() * 0.2), -0.35 - rng:NextNumber() * 0.25, 0.30 + rng:NextNumber() * 0.3).Unit
			local len = 0.17 + rng:NextNumber() * 0.10
			seg(self, name, pivot - d * 0.02, pivot + d * len, 0.085 + rng:NextNumber() * 0.02, 0.055, i % 2 == 0 and MANE or MANE_LT)
			table.insert(maneBones, name)
		end
	end
	self.maneBones = maneBones

	-- ---- head ------------------------------------------------------------------------------
	local c0, F = HEAD_C0, HEAD_F
	seg(self, "Head", c0 - F * 0.07, c0 + F * 0.50, 0.40, 0.38, HIDE, nil, HEAD_U)
	seg(self, "Head", c0 - F * 0.05, c0 + F * 0.49, 0.33, 0.46, HIDE_LT, nil, HEAD_U)
	seg(self, "Head", c0 + F * 0.46, c0 + F * 0.80, 0.285, 0.24, MUZZLE, nil, HEAD_U)
	seg(self, "Head", c0 + F * 0.47, c0 + F * 0.80, 0.225, 0.31, MUZZLE_LT, nil, HEAD_U)
	-- nostrils
	for _, side in { -1, 1 } do
		framed(self, "Head", c0 + F * 0.806 + HEAD_U * (side * 0.06) + HEAD_V * -0.03, HEAD_U, HEAD_V, V(0.05, 0.028, 0.012), HAT_BAND, PLASTIC)
	end
	-- eyes
	for _, side in { -1, 1 } do
		local e = headPt(0.46, side, 0.34, 0.004)
		framed(self, "Head", e, HEAD_U, HEAD_V, V(0.026, 0.105, 0.105), EYE_W)
		framed(self, "Head", e + HEAD_U * (side * 0.011) + HEAD_V * -0.004, HEAD_U, HEAD_V, V(0.026, 0.064, 0.07), EYE_B)
		-- brow ridge above the eye
		framed(self, "Head", headPt(0.46, side, 0.62, 0.004), HEAD_U, HEAD_V, V(0.03, 0.04, 0.10), HIDE_DK)
	end
	-- ears
	for _, side in { -1, 1 } do
		local name = side == 1 and "EarR" or "EarL"
		local base = earBase[side]
		local tip = base + V(side * 0.012, -0.075, 0.135)
		local mid = base:Lerp(tip, 0.55)
		seg(self, name, base - V(0, 0, 0.02), mid, 0.115, 0.07, HIDE)
		seg(self, name, mid - V(0, 0, 0.01), tip, 0.075, 0.048, HIDE_LT)
		seg(self, name, base + V(0, 0.032, 0.0), mid + V(0, 0.026, 0.01), 0.055, 0.02, HAT_BAND)
	end
	-- forelock
	for i, sx in { -0.5, 0, 0.5, 0.25 } do
		local p = headPt(0.06, sx * 0.7, 1.0) + V(0, 0.03, 0.01)
		local d = V(sx * 0.3, 0.55 + 0.1 * i, -0.62).Unit
		seg(self, "Head", p, p + d * (0.15 + 0.03 * (i % 2)), 0.075, 0.055, i % 2 == 0 and MANE or MANE_LT)
	end
	-- bridle
	local function strap(a: Vector3, b: Vector3, ref: Vector3)
		seg(self, "Head", a, b, 0.030, 0.012, LEATHER, FABRIC, ref)
	end
	strap(headPt(0.88, -1, 0.99, 0.014), headPt(0.88, 1, 0.99, 0.014), HEAD_F) -- noseband top
	strap(headPt(0.06, -1, 0.99, 0.014), headPt(0.06, 1, 0.99, 0.014), HEAD_F) -- crown piece
	for _, side in { -1, 1 } do
		local low = headPt(0.86, side, -0.30, 0.014)
		local mid = headPt(0.20, side, -0.30, 0.014)
		local top = headPt(0.08, side, 0.95, 0.014)
		seg(self, "Head", low, mid, 0.030, 0.012, LEATHER, FABRIC, HEAD_V)
		seg(self, "Head", mid, top, 0.030, 0.012, LEATHER, FABRIC, HEAD_F)
		seg(self, "Head", headPt(0.88, side, 0.99, 0.014), low, 0.030, 0.012, LEATHER, FABRIC, HEAD_F)
		goldRing(self, "Head", headPt(0.86, side, -0.30, 0.022), HEAD_F, HEAD_V, 0.05, 0.013)
		buckle(self, "Head", headPt(0.20, side, 0.30, 0.020), HEAD_F, HEAD_V, 0.04, 0.05)
	end
	-- bit rings + swinging chains
	self.bitRing = {}
	self.chain = { L = {}, R = {} }
	for _, side in { -1, 1 } do
		local key = side == 1 and "R" or "L"
		local ring = c0 + F * 0.645 + HEAD_U * (side * 0.152) + HEAD_V * -0.075
		goldRing(self, "Head", ring, HEAD_V, HEAD_F, 0.058, 0.014)
		self.bitRing[key] = B(ring) - self.bones.Head.rest
		local prev = "Head"
		local p = ring + V(side * 0.01, 0, -0.03)
		for i = 1, 4 do
			local bname = ("Chain%s%d"):format(key, i)
			addBone(self, bname, prev, p)
			local a = HEAD_F
			if i % 2 == 0 then
				a = V(side, 0, 0)
			end
			framed(self, bname, p + V(0, 0, -0.022), a, V(0, 0, 1), V(0.05, 0.026, 0.05), GOLD, METAL)
			framed(self, bname, p + V(0, 0, -0.02), a, V(0, 0, 1), V(0.032, 0.008, 0.052), HIDE_DK, PLASTIC)
			table.insert(self.chain[key], bname)
			prev = bname
			p = p + V(0, 0, -0.045)
		end
		goldRing(self, prev, p + V(0, 0, 0.0), V(0, 1, 0), V(0, 0, 1), 0.05, 0.012)
	end

	-- ---- tail -------------------------------------------------------------------------------
	block(self, "Tail1", V(0, -0.80, 0.98), V(0.17, 0.13, 0.22), HIDE)
	local levels = {
		{ bone = "Tail1", p = tailP1, len = 0.34 },
		{ bone = "Tail2", p = tailP2, len = 0.32 },
		{ bone = "Tail3", p = tailP3, len = 0.32 },
	}
	for li, lv in levels do
		for i = -2, 2 do
			local spread = i * 0.14
			local d = V(spread, tailDir.Y + rng:NextNumber() * 0.1, tailDir.Z + rng:NextNumber() * 0.1).Unit
			local len = lv.len * (0.9 + rng:NextNumber() * 0.25 + (li == 3 and 0.1 or 0))
			local w = 0.12 + rng:NextNumber() * 0.03 - li * 0.012
			seg(self, lv.bone, lv.p - d * 0.03, lv.p + d * len, w, 0.085 - li * 0.008, (i + li) % 2 == 0 and MANE or MANE_LT)
		end
	end

	-- ---- legs --------------------------------------------------------------------------------
	for name, leg in HorseModel.Legs do
		local hip = V(leg.x, leg.y, leg.hipY / S)
		local knee = hip - V(0, 0, leg.upper / S)
		local wide = name:sub(1, 1) == "B" and 0.26 or 0.22
		local deep = name:sub(1, 1) == "B" and 0.36 or 0.28
		seg(self, name .. "_Up", hip + V(0, 0, 0.02), knee, wide, deep, HIDE)
		seg(self, name .. "_Up", hip + V(0, 0, 0.02), knee + V(0, 0, 0.05), wide - 0.04, deep + 0.04, HIDE_LT)
		local lo = name .. "_Lo"
		local cannonEnd = knee - V(0, 0, leg.lower / S - 0.24)
		local sockEnd = knee - V(0, 0, leg.lower / S - 0.14)
		local ground = knee - V(0, 0, leg.lower / S)
		seg(self, lo, knee + V(0, 0, 0.03), cannonEnd, 0.15, 0.17, HIDE)
		seg(self, lo, cannonEnd + V(0, 0, 0.01), sockEnd, 0.178, 0.198, SOCK)
		seg(self, lo, sockEnd + V(0, 0, 0.01), ground, 0.22, 0.25, HOOF)
		self.hooves[name] = { bone = lo, offset = B(ground) - self.bones[lo].rest }
	end
end

local function buildRider(self)
	local seat = V(0, -0.03, 1.36)
	addBone(self, "Rider", "Body", seat)
	addBone(self, "RTorso", "Rider", V(0, -0.03, 1.46))
	addBone(self, "RHead", "RTorso", V(0, -0.03, 1.90))
	addBone(self, "Hat", "RHead", V(0, -0.03, 2.12))
	for _, side in { -1, 1 } do
		local key = side == 1 and "R" or "L"
		local shoulder = V(side * 0.20, -0.03, 1.82)
		addBone(self, "Arm" .. key .. "_Up", "RTorso", shoulder)
		addBone(self, "Arm" .. key .. "_Lo", "Arm" .. key .. "_Up", shoulder - V(0, 0, 0.24))
		local hip = V(side * 0.16, -0.03, 1.38)
		addBone(self, "Thigh" .. key, "Rider", hip)
		addBone(self, "Shin" .. key, "Thigh" .. key, hip - V(0, 0, 0.32))
	end
	local scarfP = V(0, -0.05, 1.88)
	local prev = "RTorso"
	for i = 1, 5 do
		addBone(self, "Scarf" .. i, prev, scarfP)
		prev = "Scarf" .. i
		scarfP = scarfP + V(0, -0.06, 0.0)
	end

	-- pelvis, torso, jacket details
	block(self, "Rider", V(0, -0.03, 1.40), V(0.30, 0.20, 0.14), PANTS)
	block(self, "RTorso", V(0, -0.03, 1.70), V(0.34, 0.20, 0.40), JACKET)
	block(self, "RTorso", V(0, -0.03, 1.66), V(0.36, 0.22, 0.30), JACKET_DK)
	block(self, "RTorso", V(0, 0.078, 1.72), V(0.07, 0.010, 0.38), CREAM)
	block(self, "RTorso", V(0, -0.03, 1.51), V(0.355, 0.215, 0.045), LEATHER_DK)
	block(self, "RTorso", V(0, 0.082, 1.51), V(0.055, 0.012, 0.045), GOLD, METAL)
	block(self, "RTorso", V(0, -0.03, 1.875), V(0.30, 0.18, 0.045), JACKET_DK) -- collar
	-- head
	block(self, "RHead", V(0, -0.03, 2.02), V(0.20, 0.20, 0.22), SKIN)
	block(self, "RHead", V(0, 0.073, 2.00), V(0.04, 0.02, 0.05), Color3.fromRGB(218, 166, 128))
	for _, sx in { -1, 1 } do
		block(self, "RHead", V(sx * 0.048, 0.072, 2.045), V(0.032, 0.012, 0.038), EYE_B)
		block(self, "RHead", V(sx * 0.048, 0.073, 2.075), V(0.05, 0.012, 0.014), HAT_BAND) -- brows
	end
	block(self, "RHead", V(0, -0.03, 2.115), V(0.205, 0.205, 0.05), HAT_BAND) -- hair under the hat
	-- hat
	block(self, "Hat", V(0, -0.03, 2.145), V(0.46, 0.46, 0.022), HAT)
	block(self, "Hat", V(0, -0.03, 2.21), V(0.25, 0.25, 0.115), HAT)
	block(self, "Hat", V(0, -0.03, 2.18), V(0.262, 0.262, 0.036), HAT_BAND)
	block(self, "Hat", V(0, -0.03, 2.275), V(0.20, 0.20, 0.012), Color3.fromRGB(196, 178, 142))
	-- arms
	for _, side in { -1, 1 } do
		local key = side == 1 and "R" or "L"
		local shoulder = V(side * 0.20, -0.03, 1.82)
		local elbow = shoulder - V(0, 0, 0.24)
		seg(self, "Arm" .. key .. "_Up", shoulder + V(0, 0, 0.03), elbow, 0.105, 0.105, JACKET)
		seg(self, "Arm" .. key .. "_Lo", elbow + V(0, 0, 0.02), elbow - V(0, 0, 0.17), 0.088, 0.088, JACKET_DK)
		seg(self, "Arm" .. key .. "_Lo", elbow - V(0, 0, 0.15), elbow - V(0, 0, 0.19), 0.095, 0.095, CREAM)
		block(self, "Arm" .. key .. "_Lo", elbow - V(0, 0, 0.23), V(0.09, 0.09, 0.075), BOOT)
		self.hand[key] = B(elbow - V(0, 0, 0.23)) - self.bones["Arm" .. key .. "_Lo"].rest
	end
	-- legs
	for _, side in { -1, 1 } do
		local key = side == 1 and "R" or "L"
		local hip = V(side * 0.16, -0.03, 1.38)
		local knee = hip - V(0, 0, 0.32)
		local ankle = knee - V(0, 0, 0.30)
		seg(self, "Thigh" .. key, hip + V(0, 0, 0.04), knee, 0.135, 0.155, PANTS)
		seg(self, "Shin" .. key, knee + V(0, 0, 0.02), ankle + V(0, 0, 0.05), 0.115, 0.125, PANTS)
		seg(self, "Shin" .. key, ankle + V(0, 0, 0.09), ankle - V(0, 0, 0.06), 0.125, 0.14, BOOT)
		block(self, "Shin" .. key, ankle + V(0, 0.045, -0.05), V(0.125, 0.20, 0.06), BOOT)
		block(self, "Shin" .. key, ankle + V(0, 0.145, -0.075), V(0.10, 0.02, 0.025), GOLD, METAL) -- spur-ish toe cap
	end
	-- scarf
	for i = 1, 5 do
		local a = V(0, -0.05 - 0.06 * (i - 1), 1.88)
		block(self, "Scarf" .. i, a + V(0, -0.03, 0), V(0.115 - i * 0.008, 0.075, 0.03), i % 2 == 0 and CREAM or RED, FABRIC)
	end
end

function HorseModel.new(opts: { rider: boolean?, outline: boolean?, seed: number? }?)
	opts = opts or {}
	local self = setmetatable({}, HorseModel)
	self.model = Instance.new("Model")
	self.model.Name = "Mount"
	self.bones = {}
	self.order = {}
	self.parts = {}
	self.hooves = {}
	self.hand = {}
	self.reins = {}
	local rng = Random.new(opts.seed or 1890)
	buildHorse(self, rng)
	if opts.rider ~= false then
		buildRider(self)
		-- reins: leather from each bit ring to the matching hand, drawn every frame
		for _, key in { "L", "R" } do
			local parts = {}
			for i = 1, 6 do
				local p = Instance.new("Part")
				p.Name = "Rein"
				p.Size = Vector3.new(0.12, 0.05, 1)
				p.Color = Color3.new(LEATHER.R * HorseModel.ColorScale, LEATHER.G * HorseModel.ColorScale, LEATHER.B * HorseModel.ColorScale)
				p.Material = FABRIC
				p.Anchored = true
				p.CanCollide = false
				p.CanQuery = false
				p.CanTouch = false
				p.CastShadow = false
				p.Parent = self.model
				parts[i] = p
			end
			table.insert(self.reins, { parts = parts, ring = self.bitRing[key], hand = self.hand[key], handBone = "Arm" .. key .. "_Lo" })
		end
	end
	-- cached arrays for BulkMoveTo
	self._parts = table.create(#self.parts)
	self._cfs = table.create(#self.parts)
	for i, entry in self.parts do
		self._parts[i] = entry.part
		self._cfs[i] = entry.part.CFrame
	end
	self.root = CFrame.identity
	if opts.outline ~= false then
		local hl = Instance.new("Highlight")
		hl.Name = "Outline"
		hl.Adornee = self.model
		hl.FillTransparency = 1
		hl.OutlineColor = Color3.fromRGB(26, 12, 8)
		hl.OutlineTransparency = 0
		hl.DepthMode = Enum.HighlightDepthMode.Occluded
		hl.Parent = self.model
	end
	self:step(CFrame.identity)
	return self
end

function HorseModel:setPose(name: string, cf: CFrame)
	local bone = self.bones[name]
	if bone then
		bone.pose = cf
	end
end

-- World CFrame of a bone from the last step (nil if the bone does not exist).
function HorseModel:boneWorld(name: string): CFrame?
	local bone = self.bones[name]
	return bone and bone.world or nil
end

function HorseModel:hoofWorld(leg: string): Vector3
	local h = self.hooves[leg]
	return self.bones[h.bone].world * h.offset
end

local REIN_SAG = 0.9

-- Recompute every bone and part from the current poses and push the result to the engine.
function HorseModel:step(rootCF: CFrame)
	self.root = rootCF
	for _, bone in self.order do
		local parent = bone.parent
		if parent then
			bone.world = parent.world * CFrame.new(bone.offset) * bone.pose
		else
			bone.world = rootCF * CFrame.new(bone.offset) * bone.pose
		end
	end
	local cfs = self._cfs
	for i, entry in self.parts do
		cfs[i] = entry.bone.world * entry.rel
	end
	if self.model:IsDescendantOf(workspace) then
		workspace:BulkMoveTo(self._parts, cfs, Enum.BulkMoveMode.FireCFrameChanged)
	else
		-- not parented yet (first step in HorseModel.new): set the CFrames one by one
		for i, part in self._parts do
			part.CFrame = cfs[i]
		end
	end

	for _, rein in self.reins do
		local a = self.bones.Head.world * rein.ring
		local b = self.bones[rein.handBone].world * rein.hand
		local n = #rein.parts
		local prev = a
		local gap = (b - a).Magnitude
		local sag = REIN_SAG + math.max(0, 7 - gap) * 0.18
		for i = 1, n do
			local t = i / n
			local p = a:Lerp(b, t) - Vector3.yAxis * (sag * 4 * t * (1 - t))
			local d = p - prev
			local len = d.Magnitude
			if len > 1e-4 then
				local part = rein.parts[i]
				part.Size = Vector3.new(0.12, 0.05, len + 0.04)
				part.CFrame = CFrame.lookAt((prev + p) / 2, p)
			end
			prev = p
		end
	end
end

function HorseModel:destroy()
	self.model:Destroy()
end

return HorseModel
