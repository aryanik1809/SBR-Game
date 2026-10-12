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
		},
	},
}
