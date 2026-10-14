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
		-- Base speed the server gives every character; the client's mount controller takes over from here.
		WalkSpeed = 22,
	},
	Mount = {
		-- Top speeds in studs/second. Hold Shift to gallop; it burns stamina.
		CanterSpeed = 22,
		GallopSpeed = 36,
		-- How quickly the horse picks up speed / slows down (1/second, higher = snappier).
		Accel = 5.5,
		Brake = 4.0,
		JumpHeight = 7,
		-- Multiplies the horse and rider colours (1 = as designed). Nudge if they look washed out or dark in Studio.
		ColorScale = 0.9,
		Stamina = {
			Max = 100,
			Drain = 24, -- per second while galloping
			Regen = 15, -- per second while not
			RegenDelay = 0.9,
			MinToSprint = 22, -- after running dry you need this much back before galloping again
		},
	},
	Feel = {
		-- Camera: how much it pulls back / widens / leads ahead of the horse at full gallop.
		ZoomOutAtGallop = 16,
		FovAtGallop = 6,
		LeadAhead = 0.4, -- seconds of velocity the camera looks ahead
		ShakeAtGallop = 0.06,
		-- Title-screen camera.
		TitlePitch = 22,
		TitleDistance = 34,
		TitleFov = 42,
		IntroSeconds = 2.4,
	},
	Fx = {
		-- Screen colour grading + bloom (client only, does not touch the world). Set false to disable.
		PostProcessing = true,
		SpeedLines = true,
	},
	Audio = {
		-- Master mix, 0..1.
		Music = 0.9,
		Sfx = 1.0,
		Ambience = 0.8,
	},
	World = {
		-- Ground is a square of this many studs per side, centered on the origin.
		Size = 1200,
		-- Props are only scattered inside this half-width.
		PropHalfExtent = 520,
		SpawnPosition = Vector3.new(0, 3, 300),
	},
}
