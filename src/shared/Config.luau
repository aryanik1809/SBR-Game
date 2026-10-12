-- Central tuning values. Change these first if something looks off in Studio.
return {
	Camera = {
		-- Angle the camera looks down at, in degrees (90 = straight down, 0 = flat horizon).
		Pitch = 50,
		-- Distance from the player in studs. Bigger = player looks smaller, like the reference.
		Distance = 120,
		-- Low FOV keeps the "flat 2D map" look (less perspective distortion).
		FieldOfView = 30,
		-- 0 = rigid follow, closer to 1 = floatier.
		Smoothing = 0.12,
	},
	Player = {
		WalkSpeed = 22,
	},
	World = {
		-- Ground is a square of this many studs per side, centered on the origin.
		Size = 1200,
		-- Props are only scattered inside this half-width.
		PropHalfExtent = 520,
		SpawnPosition = Vector3.new(0, 3, 300),
	},
}
