-- Every uploaded Roblox image ID lives here. Add new art here, nowhere else.
local function img(id: number): string
	return "rbxassetid://" .. tostring(id)
end

local Assets = {}

-- Seamless ground textures. `studs` = how many studs one copy of the image covers.
Assets.Ground = {
	Sand = { image = img(110568454119725), studs = 48 },
	Trail = { image = img(122843847820588), studs = 32 },
	-- Not placed yet: hard-edged patches look bad. Waiting on the blend overlays (#31/#32).
	Clay = { image = img(123863090800365), studs = 48 },
	Gravel = { image = img(82051725702112), studs = 48 },
}

-- Strip with dirt on the bottom 55% and transparent top 45%, laid along each trail side.
Assets.TrailEdge = {
	image = img(107028018419186),
	studsU = 48, -- along the trail
	studsV = 32, -- across the trail
	dirtFraction = 0.55,
}

-- Sprites are cut from sheets automatically: add the PNG + Roblox ID to assets/manifest.json,
-- run `python3 tools/slice_sprites.py`, and they appear here via the generated SpriteSheets module.
-- Each entry: image, rect (pixels in the source image), ppu (pixels per stud),
-- ax (pixel x of the base inside rect), collide (blocker radius in studs, nil = walk-through).
Assets.Sprites = require(script.Parent.SpriteSheets)

-- Uploaded but not placed yet. I need to see each image to cut it into sprites
-- (drop the PNGs into /assets in the repo, or paste them into the chat).
Assets.Pending = {
	TrailSandTileset = img(92826388177009), -- skipping: tiles didn't line up
	MesaCliff = img(91142423924144),
	PricklyPearBarrel = img(128913055222911),
	DesertBushes = img(126499305943725),
	GrassTufts = img(81281580303027),
	Bones = img(124875629860707),
	DesertTrees = img(85876049230931),
	RanchFence = img(84208609792015),
	StartFinishLine = img(133574185983556),
	FlagsBunting = img(125560180295696),
	Signposts = img(80586300834088),
	WagonRanchProps = img(110567161712209),
	TentGrandstand = img(75537891050075),
	CampingProps = img(90547185989154),
}

return Assets
