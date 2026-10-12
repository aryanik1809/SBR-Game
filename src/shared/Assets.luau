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

-- Sprites cut from a larger sheet. `rect` is in pixels of the 1024x1024 source image.
-- `ppu` = source pixels per stud (bigger = smaller in the world).
-- `ax` = pixel x (relative to rect) of the object's base, used to stand it on the ground.
-- `collide` = radius in studs of an invisible blocker, nil for walk-through.
Assets.Sprites = {
	cactus_tall = {
		image = img(108445753609206),
		rect = { x = 120, y = 115, w = 480, h = 805 },
		ppu = 46, ax = 250, collide = 2,
	},
	cactus_small = {
		image = img(108445753609206),
		rect = { x = 630, y = 425, w = 285, h = 490 },
		ppu = 46, ax = 100, collide = 1.5,
	},
	boulder_large = {
		image = img(96157348145725),
		rect = { x = 110, y = 120, w = 510, h = 435 },
		ppu = 34, ax = 220, collide = 6,
	},
	boulder_medium = {
		image = img(96157348145725),
		rect = { x = 570, y = 445, w = 375, h = 330 },
		ppu = 34, ax = 160, collide = 4,
	},
	boulder_small = {
		image = img(96157348145725),
		rect = { x = 240, y = 640, w = 265, h = 280 },
		ppu = 34, ax = 140, collide = 2.5,
	},
}

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
