-- Builds a flat 2D sprite standing in the 3D world, tilted to face the fixed camera.
local Config = require(script.Parent.Config)

local SpriteFactory = {}

-- Unit vector from the ground toward the camera. Sprites use it as their facing direction.
function SpriteFactory.cameraNormal(): Vector3
	local p = math.rad(Config.Camera.Pitch)
	return Vector3.new(0, math.sin(p), math.cos(p))
end

-- `def` is an entry from Assets.Sprites. `foot` is the ground point the object stands on.
function SpriteFactory.create(def, foot: Vector3, scale: number, parent: Instance): Part
	local r = def.rect
	local width = r.w / def.ppu * scale
	local height = r.h / def.ppu * scale

	local n = SpriteFactory.cameraNormal()
	-- Sprite "up": perpendicular to the camera ray, leaning slightly away from the camera.
	local up = Vector3.yAxis - n * n.Y
	up = up.Unit

	-- The bottom of the sprite rectangle sits on the ground at the base point.
	local dx = (r.w / 2 - def.ax) / def.ppu * scale
	local center = foot + Vector3.xAxis * dx + up * (height / 2)

	local part = Instance.new("Part")
	part.Name = "Sprite"
	part.Size = Vector3.new(width, height, 0.1)
	part.CFrame = CFrame.lookAt(center, center + n, Vector3.yAxis)
	part.Anchored = true
	part.CanCollide = false
	part.CanQuery = false
	part.CanTouch = false
	part.CastShadow = false
	part.Transparency = 1

	local gui = Instance.new("SurfaceGui")
	gui.Face = Enum.NormalId.Front
	gui.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
	gui.PixelsPerStud = def.ppu / scale
	gui.LightInfluence = 0
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.Parent = part

	local label = Instance.new("ImageLabel")
	label.BackgroundTransparency = 1
	label.Size = UDim2.fromScale(1, 1)
	label.Image = def.image
	label.ImageRectOffset = Vector2.new(r.x, r.y)
	label.ImageRectSize = Vector2.new(r.w, r.h)
	label.Parent = gui

	part.Parent = parent

	if def.collide then
		local block = Instance.new("Part")
		block.Name = "Collider"
		block.Size = Vector3.new(def.collide * 2 * scale, 8, def.collide * 2 * scale)
		block.Position = foot + Vector3.new(0, 4, 0)
		block.Anchored = true
		block.Transparency = 1
		block.CanQuery = false
		block.Parent = parent
	end

	return part
end

return SpriteFactory
