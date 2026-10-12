-- Layout of the first stage section. Coordinates are studs; +Z is toward the camera (screen down).
return {
	Seed = 1890,

	Trail = {
		Width = 28,
		-- Winds from the start (south, bottom of the screen) up to the north.
		Points = {
			Vector2.new(0, 360),
			Vector2.new(0, 220),
			Vector2.new(90, 120),
			Vector2.new(90, -20),
			Vector2.new(-60, -140),
			Vector2.new(-60, -360),
		},
	},

	-- Scatter rules. `weight` = relative frequency, `scale` = random size range.
	Props = {
		Count = 320,
		MinSpacing = 10,
		TrailClearance = 10, -- extra studs kept clear beside the trail
		SpawnClearance = 30,
		Kinds = {
			{ name = "cactus_tall", weight = 3, scale = { 0.8, 1.2 } },
			{ name = "cactus_small", weight = 4, scale = { 0.8, 1.2 } },
			{ name = "boulder_large", weight = 1.5, scale = { 0.8, 1.6 } },
			{ name = "boulder_medium", weight = 3, scale = { 0.8, 1.3 } },
			{ name = "boulder_small", weight = 4, scale = { 0.8, 1.4 } },
			{ name = "cactus_pricklypear", weight = 2.5, scale = { 0.8, 1.2 } },
			{ name = "cactus_barrel", weight = 2.5, scale = { 0.8, 1.2 } },
			{ name = "bones_skull", weight = 0.5, scale = { 0.8, 1.1 } },
			{ name = "bones_ribcage", weight = 0.4, scale = { 0.8, 1.1 } },
			{ name = "bones_pile", weight = 0.6, scale = { 0.8, 1.2 } },
		},
	},

	-- Hand-placed set pieces. x/z in studs.
	Landmarks = {
		{ name = "camp_fire", x = -95, z = 175, scale = 1 },
		{ name = "camp_bedroll", x = -78, z = 188, scale = 1 },
		{ name = "camp_saddle", x = -112, z = 190, scale = 1 },
	},

	-- Tall cliffs ringing the map so the edge of the world looks intentional.
	Border = {
		name = "mesa_cliff",
		distance = 540, -- from the map centre
		spacing = 58,
		scale = { 0.95, 1.25 },
	},
}
